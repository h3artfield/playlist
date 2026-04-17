from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class NikkiColumnHeaders:
    """Header row labels in the content workbook (trimmed; matched case-insensitively).

    We locate the header row as the first row that contains **every** non-null label
    among ``episode``, ``season_episode``, and ``year``. Data is then read from the
    column under each header.
    """

    episode: str = "Episode"
    season_episode: Optional[str] = "Season/Episode"
    year: Optional[str] = None
    stars: Optional[str] = "Stars"
    synopsis: Optional[str] = "Synopsis"

    @classmethod
    def standard_series(cls) -> NikkiColumnHeaders:
        """Typical series tab (Hunter, McCoys, Saint, Carol, …)."""
        return cls()

    @classmethod
    def movies_tab(cls) -> NikkiColumnHeaders:
        """``movies`` sheet: Title + Year; no season/episode column."""
        return cls(
            episode="Title",
            season_episode=None,
            year="Year",
            stars=None,
            synopsis=None,
        )


@dataclass
class Episode:
    """One playable episode row from a content workbook (or other) sheet."""

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
    # If set, overrides auto-detected content parser style (e.g. hunter, jmp, saint).
    nikki_style: Optional[str] = None
    # Optional: exact column titles from the content sheet (see ``NikkiColumnHeaders``).
    # If omitted, standard series defaults apply; ``movies`` style uses the movies tab defaults.
    nikki_columns: Optional[NikkiColumnHeaders] = None
    # Optional: only load some content rows (see ``binge_schedule.nikki`` for supported values).
    # Example: Carol Burnett tab uses green fill on playable episodes — use ``green_episode_cell``.
    nikki_row_filter: Optional[str] = None
    # Early morning repeats the **tail** of the prior calendar day's late fringe (see ``overnight_repeat``).
    # ``sunday`` → Monday 0:00–4:00 repeats Sunday 20:00–24:00 (last N slots). ``thursday`` → Friday 0:00–4:00
    # repeats Thursday 20:00–24:00. Weeks repeat the same pattern ISO week to ISO week.
    overnight_repeat_after: Optional[str] = None


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
    # JSON file (relative to the YAML file's directory unless absolute) storing next episode index per show.
    cursor_state_file: Optional[str] = None
    # Set by config loader — used to resolve relative cursor_state_file.
    config_path: Optional[Path] = None
    # Optional canonical BINGE workbook: episode codes in time order define **new** vs **rerun** (same code as
    # last airing of that show → rerun / do not advance Nikki). Applied by (weekday, half-hour slot) for later months.
    reference_binge_file: Optional[str] = None
    # Sheet name in that workbook; if omitted, the first non-notes sheet is used.
    reference_binge_sheet: Optional[str] = None
    # When true, merge episode actions from every data sheet in the workbook (all April weeks).
    reference_binge_all_sheets: bool = False
    # For each Monday YYYY-MM-DD listed, before building that ISO week set each series Nikki cursor from the
    # first chronological ``EPISODE`` code for that show in the reference BINGE (so straddle April days match April).
    reference_binge_sync_cursor_weeks: Optional[list[str]] = None
    # If set (YYYY-MM-DD), BINGE rows with calendar date **strictly before** this date are taken verbatim from
    # ``reference_binge_file`` for that ISO week. Use the first Monday of the month you are generating (e.g. May 4)
    # so Fri–Sun and overnight rows before that Monday stay canonical from the reference workbook.
    reference_binge_literal_copy_before: Optional[str] = None


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
            raise IndexError(f"No episodes loaded for show '{key}'")
        if idx >= len(eps):
            if wrap and len(eps) > 0:
                idx = idx % len(eps)
            else:
                raise IndexError(
                    f"No more episodes for show '{key}' (cursor {idx}, len {len(eps)}). "
                    "Add rows in the content workbook, lower start_episode_index, or set wrap_episodes: true in config."
                )
        ep = eps[idx]
        self.cursor[key] = idx + 1
        return ep
