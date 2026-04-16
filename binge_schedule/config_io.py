from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from binge_schedule.models import BuildConfig, ShowDef, WeekDef


def _show_from_dict(key: str, d: dict[str, Any]) -> ShowDef:
    return ShowDef(
        key=key,
        display_name=d["display_name"],
        kind=d.get("kind", "series"),
        nikki_sheet=d.get("nikki_sheet"),
        prefix=d.get("prefix", ""),
        start_episode_index=int(d.get("start_episode_index", 0)),
        nikki_style=d.get("nikki_style"),
    )


def load_build_config(path: str | Path) -> BuildConfig:
    p = Path(path)
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    shows: dict[str, ShowDef] = {}
    for key, d in (raw.get("shows") or {}).items():
        shows[key] = _show_from_dict(key, d)
    weeks: list[WeekDef] = []
    for w in raw.get("weeks") or []:
        weeks.append(
            WeekDef(
                monday=w["monday"],
                grids_file=w["grids_file"],
                sheet_name=w["sheet_name"],
            )
        )
    return BuildConfig(
        gracenote_binge_id=int(raw.get("gracenote_binge_id", 0)),
        nikki_workbook=raw["nikki_workbook"],
        shows=shows,
        weeks=weeks,
        timezone_note=str(raw.get("timezone_note", "local")),
        wrap_episodes=bool(raw.get("wrap_episodes", False)),
    )
