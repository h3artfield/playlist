from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Episode:
    """One playable episode row from a Nikki (or other) sheet."""

    raw: str
    title: str
    code: str
    episode_num: Optional[int]
    season_ep: Optional[str] = None


@dataclass
class ShowDef:
    """YAML `shows` entry."""

    key: str
    display_name: str
    kind: str  # series | literal
    nikki_sheet: Optional[str] = None
    prefix: str = ""
    # 0-based index into the loaded episode list where scheduling starts
    start_episode_index: int = 0
    # If set, overrides auto-detected Nikki parser style (e.g. hunter, jmp, saint).
    nikki_style: Optional[str] = None


@dataclass
class WeekDef:
    monday: str  # YYYY-MM-DD
    grids_file: str
    sheet_name: str


@dataclass
class BuildConfig:
    gracenote_binge_id: int
    nikki_workbook: str
    shows: dict[str, ShowDef]
    weeks: list[WeekDef]
    timezone_note: str = "local"
    # When true, episode cursors wrap to the start of each show's list after the last episode.
    wrap_episodes: bool = False


@dataclass
class BingeRow:
    date: Any  # date
    start: Any  # time or str for export
    finish: Any
    episode: str
    show: str
    episode_num: Any
    episode_name: str


@dataclass
class Segment:
    """Contiguous run of half-hour slots [start_slot, end_slot) (0..48)."""

    start_slot: int
    end_slot: int
    cell_text: str


@dataclass
class Catalog:
    """Per-show ordered episodes and mutable cursors."""

    by_show: dict[str, list[Episode]] = field(default_factory=dict)
    cursor: dict[str, int] = field(default_factory=dict)

    def next_episode(self, key: str, *, wrap: bool = False) -> Episode:
        idx = self.cursor[key]
        eps = self.by_show[key]
        if not eps:
            raise IndexError(f"No Nikki episodes loaded for show '{key}'")
        if idx >= len(eps):
            if wrap and len(eps) > 0:
                idx = idx % len(eps)
            else:
                raise IndexError(
                    f"No more episodes for show '{key}' (cursor {idx}, len {len(eps)}). "
                    "Increase Nikki rows, lower start_episode_index, or set wrap_episodes: true in config."
                )
        ep = eps[idx]
        self.cursor[key] = idx + 1
        return ep
