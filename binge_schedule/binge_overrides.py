"""Apply manual row replacements to generated BINGE dataframes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import pandas as pd


@dataclass
class BingeRowOverride:
    """Find a row by calendar date + start time, then replace all BINGE columns."""

    match_date: date
    match_start: str
    new_date: date
    new_start: str
    new_finish: str
    new_episode: str
    new_show: str
    new_episode_num: str
    new_episode_name: str


def parse_flexible_time(s: str) -> str:
    """Normalize user-entered time to 'H:MM' / 'HH:MM' like the build pipeline."""
    s = str(s).strip()
    if not s:
        raise ValueError("Empty time")
    trials = [
        s,
        s.upper(),
        s.replace(" ", ""),
        s.upper().replace(" ", ""),
    ]
    fmts = ("%I:%M %p", "%I:%M%p", "%H:%M", "%H:%M:%S")
    for cand in trials:
        for fmt in fmts:
            try:
                t = datetime.strptime(cand, fmt).time()
                return f"{t.hour}:{t.minute:02d}"
            except ValueError:
                continue
    raise ValueError(f"Unrecognized time: {s!r}")


def _time_key(s: str) -> tuple[int, int]:
    norm = parse_flexible_time(s)
    h, m = norm.split(":")
    return int(h), int(m)


def _cell_date(val: Any) -> date:
    if hasattr(val, "date") and not isinstance(val, date):
        return val.date()
    if isinstance(val, date):
        return val
    raise TypeError(f"Expected date-like, got {type(val)!r}")


def apply_binge_row_overrides(
    df: pd.DataFrame,
    overrides: list[BingeRowOverride],
    *,
    on_missing: str = "skip",
) -> tuple[pd.DataFrame, list[str]]:
    """Return a copy of ``df`` with overrides applied. Warnings if no matching row."""
    out = df.copy()
    messages: list[str] = []
    for i, o in enumerate(overrides, start=1):
        mk = _time_key(o.match_start)
        mask = []
        for _, row in out.iterrows():
            try:
                rd = _cell_date(row["DATE"])
            except (TypeError, ValueError):
                mask.append(False)
                continue
            try:
                sk = _time_key(str(row["START TIME"]))
            except ValueError:
                mask.append(False)
                continue
            mask.append(rd == o.match_date and sk == mk)
        sel = pd.Series(mask, index=out.index)
        if not sel.any():
            msg = (
                f"Override #{i}: no row matched date {o.match_date.isoformat()} "
                f"and start {o.match_start!r}."
            )
            messages.append(msg)
            if on_missing == "error":
                raise ValueError(msg)
            continue
        idx = out.index[sel][0]
        out.at[idx, "DATE"] = o.new_date
        out.at[idx, "START TIME"] = parse_flexible_time(o.new_start)
        out.at[idx, "FINISH TIME "] = parse_flexible_time(o.new_finish)
        out.at[idx, "EPISODE"] = o.new_episode
        out.at[idx, "SHOW"] = o.new_show
        out.at[idx, "EPISODE #"] = o.new_episode_num
        out.at[idx, "EPISODE NAME "] = o.new_episode_name
    return out, messages
