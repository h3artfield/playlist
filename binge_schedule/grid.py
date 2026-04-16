from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from typing import Optional

import pandas as pd

from binge_schedule.models import Segment


def load_grid_sheet(path: str, sheet_name: str) -> list[list[Optional[str]]]:
    """Return 48 rows × 7 columns of stripped strings or None."""
    df = pd.read_excel(path, sheet_name=sheet_name, header=None)
    block = df.iloc[4:52, 1:8]
    rows: list[list[Optional[str]]] = []
    for r in range(48):
        row: list[Optional[str]] = []
        for c in range(7):
            v = block.iloc[r, c]
            if pd.isna(v):
                row.append(None)
            else:
                s = str(v).strip()
                row.append(s if s else None)
        rows.append(row)
    return rows


def _is_empty(v: Optional[str]) -> bool:
    return v is None or not str(v).strip()


def segments_for_day(col: list[Optional[str]]) -> list[Segment]:
    """Split one weekday column into segments.

    - A **block** is a filled cell followed only by empty cells until the next fill.
    - A **single** is a filled cell whose immediate next row is also filled (typical strip).
    """
    if len(col) != 48:
        raise ValueError(f"Expected 48 slots, got {len(col)}")
    out: list[Segment] = []
    i = 0
    while i < 48:
        if _is_empty(col[i]):
            i += 1
            continue
        title = col[i]  # type: ignore
        if i + 1 < 48 and _is_empty(col[i + 1]):
            j = i + 1
            while j < 48 and _is_empty(col[j]):
                j += 1
            out.append(Segment(i, j, title))
            i = j
        else:
            out.append(Segment(i, i + 1, title))
            i += 1
    return out


def day_dates(week_monday: date) -> list[date]:
    return [week_monday + timedelta(days=d) for d in range(7)]


def slot_clock_to_time(slot: int) -> time:
    if not (0 <= slot < 48):
        raise ValueError(slot)
    base = datetime(2000, 1, 1, 0, 0) + timedelta(minutes=30 * slot)
    return base.time()


def slot_label(slot: int) -> str:
    """Half-hour slot as plain text (e.g. 0:00, 23:30) — no Excel time serial."""
    if not (0 <= slot < 48):
        raise ValueError(slot)
    minutes = 30 * slot
    h, m = divmod(minutes, 60)
    return f"{h}:{m:02d}"


def combine_date_time(d: date, t: time) -> datetime:
    return datetime(d.year, d.month, d.day, t.hour, t.minute, t.second)


def parse_monday(s: str) -> date:
    return date.fromisoformat(s.strip())


def parse_sheet_tab_monday(title: str) -> Optional[date]:
    """Parse a grid worksheet tab into that week's calendar anchor date (Monday in ISO configs).

    Accepts ``YYYY-MM-DD`` or legacy labels like ``4-6-2026`` (month-day-year).
    Returns ``None`` if the title does not match a known pattern.
    """
    title = title.strip()
    if not title:
        return None
    try:
        return date.fromisoformat(title)
    except ValueError:
        pass
    m = re.fullmatch(r"(\d{1,2})-(\d{1,2})-(\d{4})", title)
    if not m:
        return None
    month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return date(year, month, day)
    except ValueError:
        return None
