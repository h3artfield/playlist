from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml

from binge_schedule.models import BuildConfig, NikkiColumnHeaders, ShowDef, WeekDef

_WEEKDAY_NAMES: dict[str, int] = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}


def _morning_weekdays_from_yaml(raw: Any) -> Optional[tuple[int, ...]]:
    """Parse ``overnight_repeat_morning_weekdays``: list of 0–6 and/or weekday names (Monday=0 … Sunday=6)."""
    if raw is None:
        return None
    if not isinstance(raw, list) or not raw:
        return None
    out: list[int] = []
    for item in raw:
        if isinstance(item, int):
            if not (0 <= item <= 6):
                raise ValueError(f"overnight_repeat_morning_weekdays: invalid int {item!r} (need 0–6)")
            out.append(item)
            continue
        s = str(item).strip().lower()
        if s.isdigit():
            v = int(s)
            if not (0 <= v <= 6):
                raise ValueError(f"overnight_repeat_morning_weekdays: invalid digit {v!r} (need 0–6)")
            out.append(v)
            continue
        if s not in _WEEKDAY_NAMES:
            raise ValueError(
                f"overnight_repeat_morning_weekdays: unknown weekday {item!r} "
                f"(use monday..sunday or mon..sun, or 0–6 with Monday=0)"
            )
        out.append(_WEEKDAY_NAMES[s])
    return tuple(sorted(set(out)))


def _nikki_columns_from_dict(raw: Any) -> Optional[NikkiColumnHeaders]:
    if raw is None or raw is False:
        return None
    if not isinstance(raw, dict):
        return None
    base = NikkiColumnHeaders()

    def pick(key: str, default: str | None) -> str | None:
        if key not in raw:
            return default
        v = raw[key]
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    ep = pick("episode", base.episode) or base.episode
    se = pick("season_episode", base.season_episode)
    yr = pick("year", base.year)
    st = pick("stars", base.stars)
    sy = pick("synopsis", base.synopsis)
    return NikkiColumnHeaders(
        episode=ep,
        season_episode=se,
        year=yr,
        stars=st,
        synopsis=sy,
    )


def _show_from_dict(key: str, d: dict[str, Any]) -> ShowDef:
    return ShowDef(
        key=key,
        display_name=d["display_name"],
        kind=d.get("kind", "series"),
        nikki_sheet=d.get("nikki_sheet"),
        prefix=d.get("prefix", ""),
        start_episode_index=int(d.get("start_episode_index", 0)),
        nikki_style=d.get("nikki_style"),
        nikki_columns=_nikki_columns_from_dict(d.get("nikki_columns")),
        nikki_row_filter=(
            str(d["nikki_row_filter"]).strip()
            if d.get("nikki_row_filter") is not None and str(d.get("nikki_row_filter")).strip()
            else None
        ),
        overnight_repeat_after=(
            str(d["overnight_repeat_after"]).strip().lower()
            if d.get("overnight_repeat_after") is not None and str(d.get("overnight_repeat_after")).strip()
            else None
        ),
        overnight_repeat_pattern=(
            str(d["overnight_repeat_pattern"]).strip().lower()
            if d.get("overnight_repeat_pattern") is not None and str(d.get("overnight_repeat_pattern")).strip()
            else None
        ),
        overnight_repeat_morning_weekdays=_morning_weekdays_from_yaml(d.get("overnight_repeat_morning_weekdays")),
        repeat_previous_slot_when_unmapped=bool(d.get("repeat_previous_slot_when_unmapped", False)),
    )


def _resolve_path_relative_to_config(config_dir: Path, value: str) -> str:
    """Absolute paths stay as-is; relative paths resolve against the directory containing the setup YAML."""
    raw = Path(str(value).strip())
    if not str(raw):
        return str(raw)
    if raw.is_absolute():
        return str(raw.expanduser().resolve())
    return str((config_dir / raw).resolve())


def load_build_config(path: str | Path) -> BuildConfig:
    p = Path(path)
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    config_dir = p.parent.resolve()
    shows: dict[str, ShowDef] = {}
    for key, d in (raw.get("shows") or {}).items():
        shows[key] = _show_from_dict(key, d)
    weeks: list[WeekDef] = []
    for w in raw.get("weeks") or []:
        weeks.append(
            WeekDef(
                monday=w["monday"],
                grids_file=_resolve_path_relative_to_config(config_dir, w["grids_file"]),
                sheet_name=w["sheet_name"],
            )
        )
    csf = raw.get("cursor_state_file")
    cursor_state_file: str | None = None
    if csf is not None:
        s = str(csf).strip()
        if s:
            cursor_state_file = s
    ref = raw.get("reference_binge_file")
    reference_binge_file: str | None = None
    if ref is not None and str(ref).strip():
        reference_binge_file = str(ref).strip()
    rsh = raw.get("reference_binge_sheet")
    reference_binge_sheet: str | None = None
    if rsh is not None and str(rsh).strip():
        reference_binge_sheet = str(rsh).strip()
    return BuildConfig(
        gracenote_binge_id=int(raw.get("gracenote_binge_id", 0)),
        nikki_workbook=raw["nikki_workbook"],
        shows=shows,
        weeks=weeks,
        timezone_note=str(raw.get("timezone_note", "local")),
        wrap_episodes=bool(raw.get("wrap_episodes", False)),
        cursor_state_file=cursor_state_file,
        config_path=p.resolve(),
        reference_binge_file=reference_binge_file,
        reference_binge_sheet=reference_binge_sheet,
        reference_binge_all_sheets=bool(raw.get("reference_binge_all_sheets", False)),
        reference_binge_sync_cursor_weeks=(
            [str(x).strip() for x in raw["reference_binge_sync_cursor_weeks"] if str(x).strip()]
            if isinstance(raw.get("reference_binge_sync_cursor_weeks"), list)
            else None
        ),
        reference_binge_literal_copy_before=(
            str(raw["reference_binge_literal_copy_before"]).strip()
            if raw.get("reference_binge_literal_copy_before")
            and str(raw.get("reference_binge_literal_copy_before")).strip()
            else None
        ),
    )
