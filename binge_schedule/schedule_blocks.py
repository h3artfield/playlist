from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Iterable, Optional

from binge_schedule.grid import day_dates, segments_for_day
from binge_schedule.models import Segment
from binge_schedule.rule_analyzer import ScheduleBlock, normalize_blocks

GridMatrix = list[list[Optional[str]]]


@dataclass(frozen=True)
class CalendarBlock:
    """React-friendly schedule block derived from the weekly GRIDS matrix."""

    id: str
    start: datetime
    end: datetime
    show: str
    title: str = ""
    grid_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "start": _iso_local(self.start),
            "end": _iso_local(self.end),
            "show": self.show,
            "title": self.title,
            "grid_text": self.grid_text,
        }


def empty_week_grid() -> GridMatrix:
    return [[None for _day in range(7)] for _slot in range(48)]


def blocks_to_week_grid(
    raw_blocks: Iterable[dict[str, Any] | ScheduleBlock],
    *,
    week_monday: date,
    require_complete: bool = False,
) -> GridMatrix:
    """Convert calendar blocks into the 48×7 GRIDS matrix used by the engine.

    Continuation slots are left blank because the Excel grid represents merged
    blocks as one filled top-left cell followed by empty cells.
    """
    grid = empty_week_grid()
    occupied: dict[tuple[int, int], str] = {}
    for block in sorted(normalize_blocks(raw_blocks), key=lambda b: (b.start, b.end, b.show)):
        didx = (block.start.date() - week_monday).days
        if didx < 0 or didx > 6:
            continue
        start_slot = _datetime_to_slot_start(block.start)
        end_slot = _datetime_to_end_slot(block)
        if start_slot >= end_slot:
            continue
        text = grid_text_for_block(block)
        if not text:
            continue
        for slot in range(start_slot, end_slot):
            key = (slot, didx)
            if key in occupied:
                raise ValueError(
                    f"Overlapping schedule blocks on {block.start.date().isoformat()} "
                    f"slot {slot}: {occupied[key]!r} and {block.show!r}"
                )
            occupied[key] = block.show
        grid[start_slot][didx] = text
        for slot in range(start_slot + 1, end_slot):
            grid[slot][didx] = None
    if require_complete:
        missing = empty_slots_for_blocks(raw_blocks, week_monday=week_monday)
        if missing:
            sample = ", ".join(f"day {didx} slot {slot}" for slot, didx in missing[:5])
            raise ValueError(f"Schedule draft has {len(missing)} empty half-hour slots; first missing: {sample}")
    return grid


def grid_to_blocks(grid: GridMatrix, *, week_monday: date) -> list[CalendarBlock]:
    """Convert a 48×7 GRIDS matrix into React-friendly calendar blocks.

    GRIDS has no separate continuation marker: a filled cell followed by blanks is
    treated as one merged block until the next filled cell. Incomplete schedules
    should stay as React drafts until the user confirms they want to export them.
    """
    if len(grid) != 48:
        raise ValueError(f"Expected 48 grid rows, got {len(grid)}")
    dates = day_dates(week_monday)
    out: list[CalendarBlock] = []
    for didx, day in enumerate(dates):
        col = []
        for slot, row in enumerate(grid):
            if len(row) != 7:
                raise ValueError(f"Expected 7 columns at row {slot}, got {len(row)}")
            col.append(row[didx])
        for seg in segments_for_day(col):
            out.append(_calendar_block_from_segment(seg, day, didx))
    return out


def blocks_to_week_grids(
    raw_blocks: Iterable[dict[str, Any] | ScheduleBlock],
) -> dict[date, GridMatrix]:
    """Group calendar blocks by ISO week and return one GRIDS matrix per Monday."""
    buckets: dict[date, list[ScheduleBlock]] = defaultdict(list)
    for block in normalize_blocks(raw_blocks):
        monday = block.start.date() - timedelta(days=block.start.date().weekday())
        buckets[monday].append(block)
    return {
        monday: blocks_to_week_grid(blocks, week_monday=monday)
        for monday, blocks in sorted(buckets.items())
    }


def empty_slots_for_blocks(
    raw_blocks: Iterable[dict[str, Any] | ScheduleBlock],
    *,
    week_monday: date,
) -> list[tuple[int, int]]:
    """Return missing `(slot, day_index)` cells for a draft week."""
    occupied: set[tuple[int, int]] = set()
    for block in normalize_blocks(raw_blocks):
        didx = (block.start.date() - week_monday).days
        if didx < 0 or didx > 6:
            continue
        start_slot = _datetime_to_slot_start(block.start)
        end_slot = _datetime_to_end_slot(block)
        for slot in range(start_slot, end_slot):
            occupied.add((slot, didx))
    return [(slot, didx) for didx in range(7) for slot in range(48) if (slot, didx) not in occupied]


def grid_text_for_block(block: ScheduleBlock) -> str:
    explicit = getattr(block, "grid_text", "")
    if explicit:
        return str(explicit).strip()
    show = block.show.strip()
    title = block.episode_title.strip()
    code = block.episode_code.strip()
    content_type = block.content_type.casefold()
    if not show:
        return ""
    if code and title.casefold().startswith(f"{code.casefold()} "):
        title = title[len(code) :].strip()
    episode_bits = " ".join(x for x in (code, title) if x).strip()
    if episode_bits and "series" in content_type:
        return f"{show} - ({episode_bits})"
    if episode_bits and title and title.casefold() != show.casefold() and "movie" in content_type:
        return title
    return show


def _calendar_block_from_segment(seg: Segment, day: date, didx: int) -> CalendarBlock:
    start = _slot_to_datetime(day, seg.start_slot)
    end = _slot_to_datetime(day, seg.end_slot)
    show, title = _split_grid_text(seg.cell_text)
    return CalendarBlock(
        id=f"{day.isoformat()}-{didx}-{seg.start_slot}-{seg.end_slot}",
        start=start,
        end=end,
        show=show,
        title=title,
        grid_text=seg.cell_text,
    )


def _split_grid_text(text: str) -> tuple[str, str]:
    raw = str(text or "").strip()
    if not raw:
        return "", ""
    first = raw.splitlines()[0].strip()
    if " - (" in first and first.endswith(")"):
        show, episode = first.split(" - (", 1)
        return show.strip(), episode[:-1].strip()
    if "\n" in raw:
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        return lines[0], " ".join(lines[1:]).strip()
    return first, ""


def _datetime_to_slot_start(dt: datetime) -> int:
    minutes = dt.hour * 60 + dt.minute
    return max(0, min(47, minutes // 30))


def _datetime_to_end_slot(block: ScheduleBlock) -> int:
    if block.end.date() > block.start.date():
        return 48
    minutes = block.end.hour * 60 + block.end.minute
    return max(0, min(48, (minutes + 29) // 30))


def _slot_to_datetime(day: date, slot: int) -> datetime:
    if slot == 48:
        return datetime.combine(day + timedelta(days=1), time(0, 0))
    minutes = slot * 30
    return datetime.combine(day, time(minutes // 60, minutes % 60))


def _iso_local(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()
