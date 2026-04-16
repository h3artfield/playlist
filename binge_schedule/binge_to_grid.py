"""Build weekly48×7 grid layouts from BINGE list DataFrames."""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from binge_schedule.binge_overrides import parse_flexible_time
from binge_schedule.grid import day_dates


def _find_col(df: pd.DataFrame, *candidates: str) -> str:
    cols = {str(c).strip(): c for c in df.columns}
    for cand in candidates:
        c = cand.strip()
        if c in cols:
            return cols[c]
    raise KeyError(f"None of {candidates} found in columns {list(df.columns)!r}")


def normalize_binge_df_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    remap = {}
    cols_set = {str(c).strip() for c in out.columns}
    for c in out.columns:
        s = str(c).strip()
        if s == "FINISH TIME" and "FINISH TIME " not in [str(x).strip() for x in out.columns]:
            remap[c] = "FINISH TIME "
        elif s == "EPISODE NAME" and "EPISODE NAME " not in [
            str(x).strip() for x in out.columns
        ]:
            remap[c] = "EPISODE NAME "
    if remap:
        out = out.rename(columns=remap)
    # Some BINGE exports put the date in column A without a "DATE" header (pandas → "Unnamed: 0").
    cols_set = {str(c).strip() for c in out.columns}
    if "DATE" not in cols_set and len(out.columns) >= 2:
        c0, c1 = out.columns[0], str(out.columns[1]).strip()
        if c1 == "START TIME" and (
            str(c0).startswith("Unnamed") or not str(c0).strip()
        ):
            out = out.rename(columns={c0: "DATE"})
    return out


def parse_binge_date_cell(val: Any) -> date:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        raise ValueError("Empty date cell")
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, pd.Timestamp):
        return val.date()
    s = str(val).strip()
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        mo, d, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return date(y, mo, d)
    return date.fromisoformat(s)


def parse_binge_time_cell(val: Any) -> time:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        raise ValueError("Empty time cell")
    if isinstance(val, time):
        return val
    if isinstance(val, datetime):
        return val.time()
    if isinstance(val, pd.Timestamp):
        return val.to_pydatetime().time()
    s = str(val).strip()
    norm = parse_flexible_time(s)
    h, m = map(int, norm.split(":"))
    return time(h, m)


def wall_time_to_slot_start(t: time) -> int:
    minutes = t.hour * 60 + t.minute
    return min(47, max(0, minutes // 30))


def wall_time_to_exclusive_end_slot(t: time) -> int:
    minutes = t.hour * 60 + t.minute
    end = (minutes + 29) // 30
    return min(48, max(0, end))


def binge_row_to_grid_cell(row: pd.Series, df: pd.DataFrame) -> str:
    c_show = _find_col(df, "SHOW")
    c_ep = _find_col(df, "EPISODE")
    c_enum = _find_col(df, "EPISODE #")
    try:
        c_name = _find_col(df, "EPISODE NAME ", "EPISODE NAME")
    except KeyError:
        c_name = None

    show = str(row[c_show]).strip() if pd.notna(row[c_show]) else ""
    ep = str(row[c_ep]).strip() if pd.notna(row[c_ep]) else ""
    enum = str(row[c_enum]).strip() if pd.notna(row[c_enum]) else ""
    name = ""
    if c_name is not None and pd.notna(row.get(c_name)):
        name = str(row[c_name]).strip()

    if ep == "MOVIE":
        if name and name != show:
            return f"{show}\n{name}" if show else name
        return show or name or ep

    # One line per distinct value (literals often repeat the same title in SHOW/EPISODE/EPISODE#/NAME).
    parts = [show, ep, enum, name]
    lines: list[str] = []
    seen: set[str] = set()
    for p in parts:
        t = str(p).strip() if p else ""
        if not t:
            continue
        key = t.casefold()
        if key in seen:
            continue
        seen.add(key)
        lines.append(t)
    return "\n".join(lines) if lines else show or ep or "(program)"


def infer_monday_from_binge_df(df: pd.DataFrame) -> date:
    c_date = _find_col(df, "DATE")
    dates = [parse_binge_date_cell(r[c_date]) for _, r in df.iterrows()]
    mind = min(dates)
    return mind - timedelta(days=mind.weekday())


def split_binge_df_by_monday(df: pd.DataFrame) -> dict[date, pd.DataFrame]:
    """Split rows into ISO weeks (key = that week's Monday)."""
    c_date = _find_col(df, "DATE")
    buckets: dict[date, list[int]] = {}
    for i, row in df.iterrows():
        d = parse_binge_date_cell(row[c_date])
        mon = d - timedelta(days=d.weekday())
        buckets.setdefault(mon, []).append(i)
    return {m: df.loc[idx].copy() for m, idx in sorted(buckets.items())}


def binge_dataframe_to_grid(df: pd.DataFrame, monday: date) -> list[list[Optional[str]]]:
    """Fill a 48×7 grid from BINGE rows for the week starting ``monday``."""
    dates = day_dates(monday)
    date_to_didx = {d: i for i, d in enumerate(dates)}
    grid: list[list[Optional[str]]] = [[None] * 7 for _ in range(48)]

    c_date = _find_col(df, "DATE")
    c_start = _find_col(df, "START TIME")
    c_finish = _find_col(df, "FINISH TIME ", "FINISH TIME")

    records = [row for _, row in df.iterrows()]
    records.sort(
        key=lambda r: (
            parse_binge_date_cell(r[c_date]),
            parse_binge_time_cell(r[c_start]),
        )
    )

    for row in records:
        try:
            d = parse_binge_date_cell(row[c_date])
        except (ValueError, TypeError):
            continue
        if d not in date_to_didx:
            continue
        didx = date_to_didx[d]
        try:
            st = parse_binge_time_cell(row[c_start])
            fi = parse_binge_time_cell(row[c_finish])
        except (ValueError, TypeError):
            continue
        s0 = wall_time_to_slot_start(st)
        s1 = wall_time_to_exclusive_end_slot(fi)
        if s0 >= s1:
            continue
        text = binge_row_to_grid_cell(row, df)
        for si in range(s0, s1):
            if not (0 <= si < 48):
                continue
            if si == s0:
                grid[si][didx] = text
            else:
                grid[si][didx] = None

    return grid


def read_binge_workbook_sheets(path: Path, *, skip_notes: bool = True) -> dict[str, pd.DataFrame]:
    """Load data sheets from a BINGE-style workbook (skips **BINGE notes** when ``skip_notes``)."""
    xl = pd.ExcelFile(path)
    out: dict[str, pd.DataFrame] = {}
    for sn in xl.sheet_names:
        if skip_notes and str(sn).strip().lower() == "binge notes":
            continue
        df = pd.read_excel(path, sheet_name=sn)
        out[sn] = normalize_binge_df_columns(df)
    return out
