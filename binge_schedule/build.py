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
from binge_schedule.models import BingeRow, BuildConfig, Catalog, ShowDef
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


def resolve_show(cell: str, shows: dict[str, ShowDef]) -> tuple[str, Optional[ShowDef]]:
    cell = cell.strip()
    for key, sd in shows.items():
        dn = sd.display_name.strip()
        if cell == dn:
            return key, sd
    candidates: list[tuple[int, str, ShowDef]] = []
    for key, sd in shows.items():
        dn = sd.display_name.strip()
        if cell.startswith(dn):
            candidates.append((len(dn), key, sd))
    if candidates:
        candidates.sort(reverse=True)
        _, key, sd = candidates[0]
        return key, sd
    return "literal", None


def build_catalog(cfg: BuildConfig) -> Catalog:
    cat = Catalog()
    for key, sd in cfg.shows.items():
        if sd.kind != "series" or not sd.nikki_sheet:
            continue
        style = sd.nikki_style or nikki.default_style_for_sheet(sd.nikki_sheet)
        eps = nikki.load_sheet(
            cfg.nikki_workbook,
            sd.nikki_sheet,
            style=style,
            prefix=sd.prefix,
        )
        cat.by_show[key] = eps
        cat.cursor[key] = max(0, min(sd.start_episode_index, len(eps)))
    return cat


def _fmt_time(dt: datetime) -> str:
    return f"{dt.hour}:{dt.minute:02d}"


def rows_for_week(
    cfg: BuildConfig,
    cat: Catalog,
    grid: list[list[Optional[str]]],
    monday_s: str,
) -> list[BingeRow]:
    monday = parse_monday(monday_s)
    dates = day_dates(monday)
    rows: list[BingeRow] = []
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
                    f"Show '{key}' ({sd.display_name}) is series but Nikki episodes were not loaded. "
                    "Check nikki_sheet and kind in config."
                )

            # series
            n_slots = seg.end_slot - seg.start_slot
            for k in range(n_slots):
                slot = seg.start_slot + k
                st_dt = combine_date_time(d, slot_clock_to_time(slot))
                fin_dt = st_dt + timedelta(minutes=30)
                ep = cat.next_episode(key, wrap=cfg.wrap_episodes)
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
    rows.sort(key=lambda r: (r.date, _time_sort_key(r.start)))
    return rows


def _time_sort_key(s: str) -> tuple[int, int]:
    parts = str(s).replace(":", " ").split()
    h, m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    return h, m


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
