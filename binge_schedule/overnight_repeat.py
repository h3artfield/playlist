"""Apply scheduling rule **A**: early morning repeats the previous calendar day's late fringe.

- **Sunday → Monday** (``overnight_repeat_after: sunday``): Monday 0:00–4:00 replays the **last N** half-hours
  from **Sunday 20:00–24:00** for that show (N = Monday early row count). The same structure **repeats** each ISO week.
- **Thursday → Friday** (``overnight_repeat_after: thursday``): Friday 0:00–4:00 replays the **last N** rows from
  **Thursday 20:00–24:00**.

Runs on the **combined** BINGE dataframe (all processed weeks, including warm-up) so Sunday and Monday can align
across sheet boundaries. Nikki metadata for copied codes is filled from ``cat``.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import pandas as pd

from binge_schedule.binge_to_grid import _find_col, normalize_binge_df_columns, parse_binge_date_cell, parse_binge_time_cell
from binge_schedule.models import BuildConfig, Catalog, Episode
from binge_schedule.show_resolve import resolve_show

LATE_START = 20 * 60
LATE_END = 24 * 60
EARLY_END = 4 * 60


def _mins_from_row(row: pd.Series, c_start: str) -> int:
    t = parse_binge_time_cell(row[c_start])
    return t.hour * 60 + t.minute


def _norm_code(c: str) -> str:
    return str(c).strip().upper().replace(" ", "")


def _episode_for_code(cat: Catalog, key: str, code: str) -> Optional[Episode]:
    want = _norm_code(code)
    for e in cat.by_show.get(key, []):
        if _norm_code(e.code) == want:
            return e
    return None


def _indices_for(
    df: pd.DataFrame,
    cfg: BuildConfig,
    d: date,
    key: str,
    t0: int,
    t1: int,
    c_date: str,
    c_start: str,
    c_show: str,
) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for i, row in df.iterrows():
        try:
            rd = parse_binge_date_cell(row[c_date])
        except Exception:
            continue
        if rd != d:
            continue
        cell = str(row[c_show]).strip() if pd.notna(row[c_show]) else ""
        rk, _ = resolve_show(cell, cfg.shows)
        if rk != key:
            continue
        try:
            m = _mins_from_row(row, c_start)
        except Exception:
            continue
        if not (t0 <= m < t1):
            continue
        out.append((int(i), m))
    out.sort(key=lambda x: x[1])
    return out


def apply_overnight_repeats_combined(cfg: BuildConfig, cat: Catalog, df: pd.DataFrame) -> pd.DataFrame:
    """Return a **normalized** copy of ``df`` with overnight repeat rows patched from Nikki."""
    out = normalize_binge_df_columns(df.copy())
    try:
        c_date = _find_col(out, "DATE")
        c_start = _find_col(out, "START TIME")
        c_show = _find_col(out, "SHOW")
        c_ep = _find_col(out, "EPISODE")
        c_enum = _find_col(out, "EPISODE #")
        try:
            c_name = _find_col(out, "EPISODE NAME ", "EPISODE NAME")
        except KeyError:
            c_name = None
    except KeyError:
        return out

    sunday_keys = [
        k
        for k, sd in cfg.shows.items()
        if sd.kind == "series" and (sd.overnight_repeat_after or "").strip().lower() == "sunday"
    ]
    thursday_keys = [
        k
        for k, sd in cfg.shows.items()
        if sd.kind == "series" and (sd.overnight_repeat_after or "").strip().lower() == "thursday"
    ]

    dates = set()
    for _, row in out.iterrows():
        try:
            dates.add(parse_binge_date_cell(row[c_date]))
        except Exception:
            continue

    for d in sorted(dates):
        prev = d - timedelta(days=1)

        # Sun → Mon
        if d.weekday() == 0 and prev.weekday() == 6:
            for key in sunday_keys:
                late_idx = _indices_for(
                    out, cfg, prev, key, LATE_START, LATE_END, c_date, c_start, c_show
                )
                early_idx = _indices_for(out, cfg, d, key, 0, EARLY_END, c_date, c_start, c_show)
                if not early_idx or not late_idx:
                    continue
                late_codes = [
                    str(out.loc[ri, c_ep]).strip()
                    for ri, _ in late_idx
                    if pd.notna(out.loc[ri, c_ep]) and str(out.loc[ri, c_ep]).strip().upper() != "MOVIE"
                ]
                n = len(early_idx)
                if len(late_codes) < n:
                    continue
                take = late_codes[-n:]
                for j, (ri, _) in enumerate(early_idx):
                    code = take[j]
                    ep_obj = _episode_for_code(cat, key, code)
                    if ep_obj is None:
                        out.loc[ri, c_ep] = code
                        continue
                    out.loc[ri, c_ep] = ep_obj.code
                    out.loc[ri, c_enum] = ep_obj.episode_num
                    if c_name is not None:
                        out.loc[ri, c_name] = ep_obj.title

        # Thu → Fri
        if d.weekday() == 4 and prev.weekday() == 3:
            for key in thursday_keys:
                late_idx = _indices_for(
                    out, cfg, prev, key, LATE_START, LATE_END, c_date, c_start, c_show
                )
                early_idx = _indices_for(out, cfg, d, key, 0, EARLY_END, c_date, c_start, c_show)
                if not early_idx or not late_idx:
                    continue
                late_codes = [
                    str(out.loc[ri, c_ep]).strip()
                    for ri, _ in late_idx
                    if pd.notna(out.loc[ri, c_ep]) and str(out.loc[ri, c_ep]).strip().upper() != "MOVIE"
                ]
                n = len(early_idx)
                if len(late_codes) < n:
                    continue
                take = late_codes[-n:]
                for j, (ri, _) in enumerate(early_idx):
                    code = take[j]
                    ep_obj = _episode_for_code(cat, key, code)
                    if ep_obj is None:
                        out.loc[ri, c_ep] = code
                        continue
                    out.loc[ri, c_ep] = ep_obj.code
                    out.loc[ri, c_enum] = ep_obj.episode_num
                    if c_name is not None:
                        out.loc[ri, c_name] = ep_obj.title

    return out


def apply_overnight_repeats_with_prev(
    cfg: BuildConfig,
    cat: Catalog,
    current: pd.DataFrame,
    prev: Optional[pd.DataFrame],
    week_monday: date,
) -> pd.DataFrame:
    """Run overnight rules on ``prev`` + ``current`` combined, then keep only this ISO week’s rows."""
    from binge_schedule.grid import day_dates

    if prev is not None and not prev.empty:
        big = pd.concat(
            [
                normalize_binge_df_columns(prev.copy()),
                normalize_binge_df_columns(current.copy()),
            ],
            ignore_index=True,
        )
    else:
        big = normalize_binge_df_columns(current.copy())
    big2 = apply_overnight_repeats_combined(cfg, cat, big)
    week_dates = set(day_dates(week_monday))
    c_date = _find_col(big2, "DATE")

    def _in_week(row: pd.Series) -> bool:
        try:
            return parse_binge_date_cell(row[c_date]) in week_dates
        except Exception:
            return False

    mask = big2.apply(_in_week, axis=1)
    return big2.loc[mask].reset_index(drop=True)
