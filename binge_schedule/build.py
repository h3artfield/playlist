from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Optional

from binge_schedule.grid import (
    combine_date_time,
    day_dates,
    parse_monday,
    segments_for_day,
    slot_clock_to_time,
)
from binge_schedule.binge_pattern import EpisodeActionMap
from binge_schedule.cursor_state import resolved_nikki_workbook_path
from binge_schedule.models import BingeRow, BuildConfig, Catalog, Episode, ShowDef
from binge_schedule.show_resolve import resolve_show
from binge_schedule import nikki


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
) -> list[BingeRow]:
    """Turn one week’s **grids** program into BINGE rows.

    The grids workbook does **not** carry Nikki episode codes; it only lists *what* airs *when* (show titles,
    literals). **Episode code, episode #, and episode name** come from the Nikki workbook in playlist order.

    If ``episode_actions`` is set (from ``reference_binge_file``), each scheduled slot for a **given show** follows
    that show’s April pattern: **advance** on the first time an ``EPISODE`` code appears that week for that
    show; **repeat** replays that Nikki episode when the same code appears again. If April had a **different**
    show in that clock slot, there is no pattern for your show there—only **playlist / air order** (``next_episode``).
    Each scheduled **half-hour** is one BINGE row for series (one Nikki episode per slot), including consecutive
    strip cells with the same program title.
    """
    monday = parse_monday(monday_s)
    dates = day_dates(monday)
    rows: list[BingeRow] = []
    # (show_key, weekday, slot) -> Episode emitted for that clock position (for repeat refs).
    emitted: dict[tuple[str, int, int], Episode] = {}
    for day_index in range(7):
        d = dates[day_index]
        col = [grid[r][day_index] for r in range(48)]
        for seg in segments_for_day(col):
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

            # series — one half-hour row per slot; advance vs repeat from optional reference BINGE actions.
            n_slots = seg.end_slot - seg.start_slot
            wd = d.weekday()
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
