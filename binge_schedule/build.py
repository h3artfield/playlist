from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Optional

import pandas as pd

from binge_schedule.grid import (
    combine_date_time,
    day_dates,
    parse_monday,
    segments_for_binge_scheduling,
    slot_clock_to_time,
)
from binge_schedule.binge_pattern import EpisodeActionMap
from binge_schedule.cursor_state import resolved_nikki_workbook_path
from binge_schedule.models import BingeRow, BuildConfig, Catalog, Episode, ShowDef
from binge_schedule.show_resolve import resolve_show
from binge_schedule import nikki
from binge_schedule.binge_to_grid import normalize_binge_df_columns

from binge_schedule.overnight_repeat import (
    LATE_END,
    LATE_START,
    _episode_for_code as _episode_for_catalog_code,
    _overnight_repeat_mode,
)


def _norm_binge_date(obj: object) -> date:
    if hasattr(obj, "date") and callable(getattr(obj, "date")):
        obj = obj.date()
    assert isinstance(obj, date)
    return obj


def _binge_row_start_mins_midnight(br: BingeRow) -> int:
    hs = str(br.start).replace(":", " ").split()
    h, m = int(hs[0]), int(hs[1]) if len(hs) > 1 else 0
    # Treat 24:xx as prior day edge if ever seen; grid uses 0:004:00 overnight.
    return h * 60 + m


def _late_series_eps_prior_day_default_pattern(
    cfg: BuildConfig,
    cat: Catalog,
    series_key: str,
    prior_day: date,
    completed_rows: list[BingeRow],
    prev_completed_week_df: Optional[pd.DataFrame],
) -> list[Episode]:
    """Chronological Episode objects for ``series_key`` on ``prior_day`` in 20:0024:00."""

    cand: list[tuple[int, Episode]] = []
    seen: set[tuple[int, str]] = set()

    def append_ep(minutes: int, ep_o: Episode) -> None:
        sig = (minutes, str(ep_o.code))
        if sig in seen:
            return
        seen.add(sig)
        cand.append((minutes, ep_o))

    for br in completed_rows:
        rk, _sd = resolve_show(br.show, cfg.shows)
        if rk != series_key:
            continue
        d0 = _norm_binge_date(br.date)
        if d0 != prior_day:
            continue
        m = _binge_row_start_mins_midnight(br)
        if not (LATE_START <= m < LATE_END):
            continue
        code_raw = str(br.episode).strip()
        if not code_raw or code_raw.upper() == "MOVIE":
            continue
        ep_o = _episode_for_catalog_code(cat, series_key, code_raw)
        if ep_o is None:
            continue
        append_ep(m, ep_o)

    if prev_completed_week_df is not None:
        from binge_schedule.binge_to_grid import _find_col, parse_binge_date_cell, parse_binge_time_cell

        df = normalize_binge_df_columns(prev_completed_week_df.copy())
        c_date = _find_col(df, "DATE")
        c_start = _find_col(df, "START TIME")
        c_show = _find_col(df, "SHOW")
        c_ep = _find_col(df, "EPISODE")
        for _, row in df.iterrows():
            try:
                rd = parse_binge_date_cell(row[c_date])
            except (ValueError, TypeError):
                continue
            if rd != prior_day:
                continue
            rk, _sd = resolve_show(str(row[c_show]).strip() if pd.notna(row[c_show]) else "", cfg.shows)
            if rk != series_key:
                continue
            try:
                t = parse_binge_time_cell(row[c_start])
            except (ValueError, TypeError):
                continue
            m = t.hour * 60 + t.minute
            if not (LATE_START <= m < LATE_END):
                continue
            code_raw = str(row[c_ep]).strip() if pd.notna(row[c_ep]) else ""
            if not code_raw or code_raw.upper() == "MOVIE":
                continue
            ep_o = _episode_for_catalog_code(cat, series_key, code_raw)
            if ep_o is None:
                continue
            append_ep(m, ep_o)

    cand.sort(key=lambda x: x[0])
    return [e for _m, e in cand]


def _segment_default_daily_overnight_early(sd: ShowDef, seg, d: date) -> bool:
    if sd.kind != "series" or _overnight_repeat_mode(sd.overnight_repeat_after) != "daily":
        return False
    pat = (sd.overnight_repeat_pattern or "default").strip().lower()
    if pat != "default":
        return False
    if sd.overnight_repeat_morning_weekdays is not None:
        if d.weekday() not in sd.overnight_repeat_morning_weekdays:
            return False
    return seg.start_slot >= 0 and seg.end_slot <= 8

def _short_program_title(cell: str) -> str:
    line = cell.split("\n")[0].strip()
    for sep in (" - (", "-(", " ("):
        if sep in line:
            return line.split(sep)[0].strip()
    return line[:240]


def _literal_episode_name(cell: str) -> str:
    s = cell.strip()
    p = s.find("(")
    if p >= 0:
        return s[p:].strip()
    return s


def build_catalog(cfg: BuildConfig) -> Catalog:
    """Load each series’ episode list from the content workbook.

    Respects per-show ``nikki_row_filter`` (e.g. ``green_episode_cell`` for Carol Burnett): only those
    rows exist in ``cat.by_show``, so scheduling never pulls a disallowed episode.
    """
    cat = Catalog()
    wb_path = str(resolved_nikki_workbook_path(cfg))
    for key, sd in cfg.shows.items():
        if sd.kind != "series" or not sd.nikki_sheet:
            continue
        style = sd.nikki_style or nikki.default_style_for_sheet(sd.nikki_sheet)
        cols = nikki.effective_column_headers(sd, style=style)
        eps = nikki.load_sheet(
            wb_path,
            sd.nikki_sheet,
            style=style,
            prefix=sd.prefix,
            columns=cols,
            row_filter=sd.nikki_row_filter,
        )
        cat.by_show[key] = eps
        cat.cursor[key] = max(0, min(sd.start_episode_index, len(eps)))
    return cat


def _fmt_time(dt: datetime) -> str:
    return f"{dt.hour}:{dt.minute:02d}"


def _episode_for_slot(
    cfg: BuildConfig,
    cat: Catalog,
    key: str,
    wd: int,
    slot: int,
    episode_actions: Optional[EpisodeActionMap],
    emitted: dict[tuple[str, int, int], Episode],
) -> Episode:
    """Resolve Nikki episode for this clock slot using optional canonical April actions.

    Lookup is ``(show_key, weekday, slot)``. Missing entry means no reference rule for this show in this
    half-hour (e.g. different show occupied that slot in April, or programming changed)—use normal
    **air-date** order via ``next_episode``, unless ``ShowDef.repeat_previous_slot_when_unmapped`` replays the
    prior half-hour on the same day for that show.
    """
    if not episode_actions:
        ep = cat.next_episode(key, wrap=cfg.wrap_episodes)
        emitted[(key, wd, slot)] = ep
        return ep

    act = episode_actions.get((key, wd, slot))
    if act is None:
        sd0 = cfg.shows.get(key)
        if (
            sd0 is not None
            and sd0.kind == "series"
            and sd0.repeat_previous_slot_when_unmapped
            and slot > 0
        ):
            prev_ep = emitted.get((key, wd, slot - 1))
            if prev_ep is not None:
                emitted[(key, wd, slot)] = prev_ep
                return prev_ep
        ep = cat.next_episode(key, wrap=cfg.wrap_episodes)
        emitted[(key, wd, slot)] = ep
        return ep
    if act == "advance":
        ep = cat.next_episode(key, wrap=cfg.wrap_episodes)
        emitted[(key, wd, slot)] = ep
        return ep

    assert act[0] == "repeat"
    _, wd_r, sl_r = act
    ref = emitted.get((key, wd_r, sl_r))
    if ref is None:
        ep = cat.next_episode(key, wrap=cfg.wrap_episodes)
        emitted[(key, wd, slot)] = ep
        return ep
    emitted[(key, wd, slot)] = ref
    return ref


def rows_for_week(
    cfg: BuildConfig,
    cat: Catalog,
    grid: list[list[Optional[str]]],
    monday_s: str,
    *,
    episode_actions: Optional[EpisodeActionMap] = None,
    prev_completed_week_binge_df: Optional[pd.DataFrame] = None,
) -> list[BingeRow]:
    """Turn one week’s **grids** program into BINGE rows.

    The grids workbook does **not** carry Nikki episode codes; it only lists *what* airs *when* (show titles,
    literals). **Episode code, episode #, and episode name** come from the Nikki workbook in schedule order.

    If ``episode_actions`` is set (from ``reference_binge_file``), each scheduled slot for a **given show** follows
    that show’s April pattern: **advance** on the first time an ``EPISODE`` code appears that week for that
    show; **repeat** replays that Nikki episode when the same code appears again. If April had a **different**
    show in that clock slot, there is no pattern for your show there—only **schedule / air order** (``next_episode``).
    **30-minute** series (default): one BINGE row per half-hour. **60** / **120** ``binge_row_minutes`` merge grid
    half-hours into one row per episode block (April template); reference BINGE typos do not override YAML.

    For shows with ``overnight_repeat_after`` matching the **default daily** fringe rule, segments in **0:00–4:00**
    reuse the prior calendar day’s late-fringe episodes (Nikki advances only afterward). Monday mornings use rows
    from ``prev_completed_week_binge_df`` when the grid run has not produced Sunday night yet.
    """
    monday = parse_monday(monday_s)
    dates = day_dates(monday)
    rows: list[BingeRow] = []
    # (show_key, weekday, slot) -> Episode emitted for that clock position (for repeat refs).
    emitted: dict[tuple[str, int, int], Episode] = {}
    for day_index in range(7):
        d = dates[day_index]
        col = [grid[r][day_index] for r in range(48)]
        for seg in segments_for_binge_scheduling(col, cfg):
            key, sd = resolve_show(seg.cell_text, cfg.shows)
            if sd is None or key == "literal":
                n_slots = seg.end_slot - seg.start_slot
                if n_slots == 1:
                    st_dt = combine_date_time(d, slot_clock_to_time(seg.start_slot))
                    fin_dt = st_dt + timedelta(minutes=30)
                    st = _short_program_title(seg.cell_text)
                    rows.append(
                        BingeRow(
                            date=d,
                            start=_fmt_time(st_dt),
                            finish=_fmt_time(fin_dt),
                            episode=st,
                            show=st,
                            episode_num=st,
                            episode_name=_literal_episode_name(seg.cell_text),
                        )
                    )
                else:
                    st_dt = combine_date_time(d, slot_clock_to_time(seg.start_slot))
                    fin_dt = st_dt + timedelta(minutes=30 * n_slots)
                    st = _short_program_title(seg.cell_text)
                    rows.append(
                        BingeRow(
                            date=d,
                            start=_fmt_time(st_dt),
                            finish=_fmt_time(fin_dt),
                            episode="MOVIE",
                            show=st,
                            episode_num="MOVIE",
                            episode_name=_literal_episode_name(seg.cell_text),
                        )
                    )
                continue

            if sd.kind == "literal":
                n_slots = seg.end_slot - seg.start_slot
                if n_slots == 1:
                    st_dt = combine_date_time(d, slot_clock_to_time(seg.start_slot))
                    fin_dt = st_dt + timedelta(minutes=30)
                    lit = sd.display_name
                    rows.append(
                        BingeRow(
                            date=d,
                            start=_fmt_time(st_dt),
                            finish=_fmt_time(fin_dt),
                            episode=lit,
                            show=lit,
                            episode_num=lit,
                            episode_name=lit,
                        )
                    )
                else:
                    st_dt = combine_date_time(d, slot_clock_to_time(seg.start_slot))
                    fin_dt = st_dt + timedelta(minutes=30 * n_slots)
                    st = _short_program_title(seg.cell_text)
                    rows.append(
                        BingeRow(
                            date=d,
                            start=_fmt_time(st_dt),
                            finish=_fmt_time(fin_dt),
                            episode="MOVIE",
                            show=st,
                            episode_num="MOVIE",
                            episode_name=_literal_episode_name(seg.cell_text),
                        )
                    )
                continue

            if key not in cat.by_show:
                raise KeyError(
                    f"Show '{key}' ({sd.display_name}) is series but episodes were not loaded from the content workbook. "
                    "Check nikki_sheet and kind in config."
                )

            # series — advance vs repeat from optional reference BINGE actions.
            n_slots = seg.end_slot - seg.start_slot
            wd = d.weekday()
            brm = int(getattr(sd, "binge_row_minutes", 30) or 30)
            want_slots = brm // 30 if brm > 30 and brm % 30 == 0 else 0

            prior_day = d - timedelta(days=1)
            if (
                brm == 30
                and want_slots == 0
                and _segment_default_daily_overnight_early(sd, seg, d)
            ):
                late_eps = _late_series_eps_prior_day_default_pattern(
                    cfg,
                    cat,
                    key,
                    prior_day,
                    rows,
                    prev_completed_week_binge_df,
                )
                n_need = n_slots
                if len(late_eps) >= n_need:
                    tail = late_eps[-n_need:]
                    for kdx in range(n_need):
                        slot = seg.start_slot + kdx
                        ep = tail[kdx]
                        emitted[(key, wd, slot)] = ep
                        st_dt = combine_date_time(d, slot_clock_to_time(slot))
                        fin_dt = st_dt + timedelta(minutes=30)
                        rows.append(
                            BingeRow(
                                date=d,
                                start=_fmt_time(st_dt),
                                finish=_fmt_time(fin_dt),
                                episode=ep.code,
                                show=sd.display_name,
                                episode_num=ep.episode_num,
                                episode_name=ep.title,
                            )
                        )
                    continue

            if want_slots > 0 and n_slots == want_slots:
                slot0 = seg.start_slot
                ep = _episode_for_slot(
                    cfg,
                    cat,
                    key,
                    wd,
                    slot0,
                    episode_actions,
                    emitted,
                )
                for off in range(1, n_slots):
                    emitted[(key, wd, slot0 + off)] = ep
                st_dt = combine_date_time(d, slot_clock_to_time(slot0))
                fin_dt = st_dt + timedelta(minutes=brm)
                rows.append(
                    BingeRow(
                        date=d,
                        start=_fmt_time(st_dt),
                        finish=_fmt_time(fin_dt),
                        episode=ep.code,
                        show=sd.display_name,
                        episode_num=ep.episode_num,
                        episode_name=ep.title,
                    )
                )
            else:
                for k in range(n_slots):
                    slot = seg.start_slot + k
                    st_dt = combine_date_time(d, slot_clock_to_time(slot))
                    fin_dt = st_dt + timedelta(minutes=30)
                    ep = _episode_for_slot(
                        cfg,
                        cat,
                        key,
                        wd,
                        slot,
                        episode_actions,
                        emitted,
                    )
                    rows.append(
                        BingeRow(
                            date=d,
                            start=_fmt_time(st_dt),
                            finish=_fmt_time(fin_dt),
                            episode=ep.code,
                            show=sd.display_name,
                            episode_num=ep.episode_num,
                            episode_name=ep.title,
                        )
                    )
    rows.sort(key=_binge_row_sort_datetime)
    return rows


def _time_sort_key(s: str) -> tuple[int, int]:
    parts = str(s).replace(":", " ").split()
    h, m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    return h, m


def _binge_row_sort_datetime(r: BingeRow) -> datetime:
    """Stable chronological order (fixes Thu 23:30 vs Fri 0:00 when date/time types mix)."""
    d = r.date
    if hasattr(d, "date"):
        d = d.date()
    h, m = _time_sort_key(str(r.start))
    return datetime(d.year, d.month, d.day, h, m)


def build_grids_matrix(
    monday: date,
    grid: list[list[Optional[str]]],
    gracenote_binge_id: int,
) -> list[list[object]]:
    """52×9 matrix matching reference layout (values only)."""
    out: list[list[object]] = []
    out.append([".", None, None, None, "BINGE", None, None, None, None])
    r1 = [None] * 9
    r1[4] = f"Gracenote BINGE ID: {gracenote_binge_id}"
    out.append(r1)
    row2: list[object] = [None]
    for i in range(7):
        row2.append(datetime.combine(monday + timedelta(days=i), time()))
    row2.append(None)
    out.append(row2)
    out.append(["BINGE", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "BINGE"])
    for r in range(48):
        t = slot_clock_to_time(r)
        row: list[object] = [t]
        for c in range(7):
            v = grid[r][c]
            row.append(v if v is not None else None)
        row.append(t)
        out.append(row)
    return out
