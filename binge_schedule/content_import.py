from __future__ import annotations

import json
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from binge_schedule.config_io import BuildConfig

IMPORT_ALIASES: dict[str, set[str]] = {
    "series_title": {
        "series title",
        "series name",
        "series",
        "show",
        "show title",
        "program",
        "program title",
    },
    "title": {
        "title",
        "episode",
        "episode title",
        "movie title",
        "asset title",
    },
    "episode_number": {
        "episode number",
        "season/episode",
        "ep #",
        "episode #",
    },
    "runtime": {"runtime", "duration", "length", "run time", "run time (min)", "trt"},
    "slot": {"slot", "grid slot", "slot length", "binge slot", "block length"},
    "content_type": {"content type", "type", "category"},
    "genre": {"genre", "category"},
    "original_airdate": {"original airdate", "airdate", "year", "release date"},
    "synopsis_short": {"synopsis short", "short synopsis", "short description"},
    "synopsis_long": {"synopsis long", "long synopsis", "description"},
    "copyright": {"copyright", "rights"},
    "playable": {
        "playable",
        "cleared to air",
        "can air",
        "approved to air",
        "air ok",
        "schedule",
        "cleared",
        "approved",
    },
}


PLAYABLE_YES_VALUES = frozenset(
    {"yes", "y", "true", "1", "x", "playable", "cleared", "ok", "available", "approved"}
)
PLAYABLE_NO_VALUES = frozenset(
    {"no", "n", "false", "0", "hold", "blocked", "unavailable", "not available", "do not air", "hold back"}
)
PLAYABLE_BLANK_VALUES = frozenset({"", "nan", "none", "null", "nat", "-", "n/a", "na", "tbd", "pending"})
VALID_SLOT_MINUTES = frozenset({30, 60, 120})


def _slot_minutes_from_time_parts(hours: int, minutes: int, seconds: int) -> Optional[int]:
    if seconds not in (0,):
        total = hours * 60 + minutes + (1 if seconds >= 30 else 0)
        return total if total in VALID_SLOT_MINUTES else None
    if hours in VALID_SLOT_MINUTES and minutes == 0:
        return hours
    if hours in {1, 2} and minutes == 0:
        return hours * 60
    if hours == 0 and minutes in VALID_SLOT_MINUTES:
        return minutes
    total = hours * 60 + minutes
    return total if total in VALID_SLOT_MINUTES else None


def parse_slot_minutes_cell(value: Any) -> Optional[int]:
    """Return 30, 60, or 120 for explicit grid slot values; blank/invalid = None."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, (int, float)) and not pd.isna(value):
        fv = float(value)
        if fv in VALID_SLOT_MINUTES:
            return int(fv)
        if 0 < fv < 1:
            minutes = int(round(fv * 24 * 60))
            return minutes if minutes in VALID_SLOT_MINUTES else None
        minutes = int(round(fv))
        return minutes if minutes in VALID_SLOT_MINUTES else None
    if hasattr(value, "total_seconds"):
        try:
            minutes = int(round(float(value.total_seconds()) / 60.0))
        except Exception:
            return None
        return minutes if minutes in VALID_SLOT_MINUTES else None
    text = " ".join(str(value).strip().split())
    if not text or text.lower() in PLAYABLE_BLANK_VALUES:
        return None
    if ":" in text:
        parts = text.split(":")
        try:
            nums = [int(float(part)) for part in parts]
        except ValueError:
            return None
        if len(nums) == 3:
            return _slot_minutes_from_time_parts(nums[0], nums[1], nums[2])
        if len(nums) == 2:
            hours, minutes = nums
            if hours in VALID_SLOT_MINUTES and minutes == 0:
                return hours
            return _slot_minutes_from_time_parts(hours, minutes, 0)
    try:
        minutes = int(round(float(text)))
    except ValueError:
        return None
    return minutes if minutes in VALID_SLOT_MINUTES else None


def parse_playable_cell(value: Any) -> bool:
    """Return True only for explicit yes-like values. Blank or unknown = False."""
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except Exception:
        pass
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not pd.isna(value):
        if int(value) == 1:
            return True
        if int(value) == 0:
            return False
    text = " ".join(str(value).strip().lower().split())
    if text in PLAYABLE_BLANK_VALUES:
        return False
    if text in PLAYABLE_YES_VALUES:
        return True
    if text in PLAYABLE_NO_VALUES:
        return False
    return False


def imported_row_is_playable(row: dict[str, Any]) -> bool:
    """Legacy imported rows without ``playable`` stay schedulable; explicit False is not."""
    if "playable" not in row:
        return True
    value = row.get("playable")
    if isinstance(value, bool):
        return value
    return parse_playable_cell(value)


def find_playable_header_index(header_map: dict[str, int]) -> int | None:
    playable_aliases = IMPORT_ALIASES["playable"]
    for alias in playable_aliases:
        idx = header_map.get(alias)
        if idx is not None:
            return idx
    return None


def imported_catalog_path(cfg: BuildConfig) -> Path:
    from binge_schedule.runtime_paths import imported_catalog_path as resolve_imported_catalog_path

    cfg_file = cfg.config_path.resolve() if cfg.config_path is not None else None
    return resolve_imported_catalog_path(cfg_file)


def _normalize_key(text: Any) -> str:
    value = " ".join(str(text or "").strip().lower().split())
    return "" if value in {"nan", "none", "null", "nat"} else value


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _normalize_episode_number(value: Any) -> str:
    raw = _normalize_key(value)
    if not raw:
        return ""
    if re.fullmatch(r"\d+", raw):
        return str(int(raw))
    return raw


def import_row_identity_key(row: dict[str, Any]) -> str:
    kind = _normalize_key(row.get("content_type", ""))
    series_title = _normalize_key(row.get("series_title", ""))
    display_name = _normalize_key(row.get("display_name", ""))
    ep_num = _normalize_episode_number(row.get("episode_number", ""))
    ep_title = _normalize_key(row.get("episode_title", ""))
    if kind == "series":
        base = series_title or display_name
        episode_token = ep_num or ep_title
        return f"{kind}|{base}|{episode_token}"
    return f"{kind or 'movie'}|{display_name or series_title}"


def dedupe_import_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        key = import_row_identity_key(row)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def load_imported_catalog_rows(cfg: BuildConfig) -> list[dict[str, Any]]:
    path = imported_catalog_path(cfg)
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(raw, dict):
        rows = raw.get("rows", [])
        if isinstance(rows, list):
            return dedupe_import_rows([row for row in rows if isinstance(row, dict)])
    if isinstance(raw, list):
        return dedupe_import_rows([row for row in raw if isinstance(row, dict)])
    return []


def save_imported_catalog_rows(cfg: BuildConfig, rows: list[dict[str, Any]]) -> Path:
    path = imported_catalog_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"rows": dedupe_import_rows(rows)}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def merge_import_rows(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = dedupe_import_rows(list(existing))
    seen_idx: dict[str, int] = {}
    for index, row in enumerate(out):
        seen_idx[import_row_identity_key(row)] = index
    for row in incoming:
        key = import_row_identity_key(row)
        if key in seen_idx:
            out[seen_idx[key]] = row
        else:
            seen_idx[key] = len(out)
            out.append(row)
    return dedupe_import_rows(out)


def _runtime_parts_to_minutes(hours: int, minutes: int, seconds: int = 0, *, two_part: bool = False) -> int:
    """Parse TRT from Excel time or MM:SS / H:MM:SS values."""
    if two_part:
        if hours >= 10 and minutes < 60:
            return max(1, int(round(hours + minutes / 60.0 + seconds / 3600.0)))
        return max(1, int(round(hours * 60 + minutes + seconds / 60.0)))
    return max(1, hours * 60 + minutes)


def _runtime_minutes_from_cell(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, (int, float)):
        fv = float(value)
        if 0 < fv < 1:
            return max(1, int(round(fv * 24 * 60)))
        return max(1, int(round(fv)))
    if hasattr(value, "hour") and hasattr(value, "minute"):
        try:
            hours = int(value.hour)
            minutes = int(value.minute)
            seconds = int(getattr(value, "second", 0) or 0)
            if hours >= 10 and minutes < 60:
                return _runtime_parts_to_minutes(hours, minutes, seconds, two_part=True)
            return _runtime_parts_to_minutes(hours, minutes, seconds)
        except Exception:
            pass
    if hasattr(value, "total_seconds"):
        try:
            total_secs = int(round(float(value.total_seconds())))
        except Exception:
            return None
        if total_secs < 0:
            return None
        hours, rem = divmod(total_secs, 3600)
        minutes, seconds = divmod(rem, 60)
        if hours >= 10 and minutes < 60:
            return _runtime_parts_to_minutes(hours, minutes, seconds, two_part=True)
        return _runtime_parts_to_minutes(hours, minutes, seconds)
    text = str(value).strip()
    if not text:
        return None
    if ":" in text:
        parts = text.split(":")
        try:
            nums = [int(float(part)) for part in parts]
        except ValueError:
            return None
        if len(nums) == 3:
            return _runtime_parts_to_minutes(nums[0], nums[1], nums[2])
        if len(nums) == 2:
            return _runtime_parts_to_minutes(nums[0], nums[1], 0, two_part=True)
    try:
        return max(1, int(round(float(text))))
    except ValueError:
        return None


def _column_map(df: pd.DataFrame) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for column in df.columns:
        normalized = _normalize_key(column)
        for canon, aliases in IMPORT_ALIASES.items():
            if normalized in aliases and canon not in mapping:
                mapping[canon] = str(column)
    return mapping


def rows_from_dataframe(df: pd.DataFrame, *, sheet_name: str, source_name: str) -> list[dict[str, Any]]:
    col_map = _column_map(df)
    out: list[dict[str, Any]] = []
    for _, record in df.iterrows():
        series_title = _clean_text(record.get(col_map.get("series_title", ""), ""))
        title = _clean_text(record.get(col_map.get("title", ""), ""))
        ep_num = _clean_text(record.get(col_map.get("episode_number", ""), ""))
        raw_type = _clean_text(record.get(col_map.get("content_type", ""), "")).lower()
        if raw_type in {"movie", "movies", "special", "specials", "film", "feature"}:
            is_series = False
        elif raw_type in {"series", "show", "episode"}:
            is_series = True
        else:
            is_series = bool(series_title and (ep_num or title))
        if is_series and not series_title:
            series_title = sheet_name.strip()
        display = series_title if is_series else title
        if not display:
            continue
        runtime = _runtime_minutes_from_cell(record.get(col_map.get("runtime", ""), None))
        slot_minutes = None
        if raw_type not in {"movie", "movies", "special", "specials", "film", "feature"}:
            slot_minutes = parse_slot_minutes_cell(record.get(col_map.get("slot", ""), None))
        air_raw = record.get(col_map.get("original_airdate", ""), None)
        air_iso = ""
        try:
            if pd.notna(air_raw):
                air_iso = pd.to_datetime(air_raw).date().isoformat()
        except Exception:
            air_iso = _clean_text(air_raw)
        playable_col = col_map.get("playable")
        if playable_col:
            playable = parse_playable_cell(record.get(playable_col, None))
        else:
            playable = True
        out.append(
            {
                "content_type": "series" if is_series else "movie",
                "display_name": display,
                "series_title": series_title if is_series else "",
                "episode_number": ep_num if is_series else "",
                "episode_title": title if is_series else "",
                "genre": _clean_text(record.get(col_map.get("genre", ""), "")).split(",")[0].strip().lower(),
                "runtime_minutes": runtime,
                "slot_minutes": slot_minutes,
                "original_airdate": air_iso,
                "copyright": _clean_text(record.get(col_map.get("copyright", ""), "")),
                "synopsis_short": _clean_text(record.get(col_map.get("synopsis_short", ""), "")),
                "synopsis_long": _clean_text(record.get(col_map.get("synopsis_long", ""), "")),
                "playable": playable,
                "source_sheet": sheet_name,
                "source_file": source_name,
            }
        )
    return out


def parse_upload_file(filename: str, payload: bytes) -> list[dict[str, Any]]:
    name = str(filename or "").strip()
    lower = name.lower()
    rows: list[dict[str, Any]] = []
    if lower.endswith(".csv"):
        df = pd.read_csv(BytesIO(payload))
        rows.extend(rows_from_dataframe(df, sheet_name="CSV", source_name=name))
        return rows
    if lower.endswith((".xlsx", ".xls")):
        workbook = pd.ExcelFile(BytesIO(payload))
        for sheet_name in workbook.sheet_names:
            df = pd.read_excel(BytesIO(payload), sheet_name=sheet_name)
            rows.extend(rows_from_dataframe(df, sheet_name=sheet_name, source_name=name))
        return rows
    raise ValueError("Upload a CSV or Excel (.xlsx) file.")


def build_manual_row(
    *,
    content_type: str,
    show_name: str,
    episode_number: str = "",
    episode_title: str = "",
    runtime_minutes: Optional[int] = None,
    slot_minutes: Optional[int] = None,
    genre: str = "",
) -> dict[str, Any]:
    show = _clean_text(show_name)
    if not show:
        raise ValueError("Show or title is required.")
    normalized_type = _normalize_key(content_type)
    is_series = normalized_type in {"series", "show", "episode"}
    ep_num = _clean_text(episode_number)
    ep_title = _clean_text(episode_title)
    if is_series and not ep_num and not ep_title:
        raise ValueError("Series rows need an episode number or episode title.")
    row: dict[str, Any] = {
        "content_type": "series" if is_series else normalized_type or "movie",
        "display_name": show,
        "series_title": show if is_series else "",
        "episode_number": ep_num if is_series else "",
        "episode_title": ep_title if is_series else "",
        "genre": _clean_text(genre).lower(),
        "runtime_minutes": runtime_minutes,
        "source_sheet": "manual",
        "source_file": "schedule_builder",
    }
    if slot_minutes is not None:
        row["slot_minutes"] = slot_minutes
    return row


def catalog_publish_paths() -> list[Path]:
    from binge_schedule.runtime_paths import catalog_publish_targets

    return catalog_publish_targets()


def publish_content_catalog(cfg: BuildConfig) -> tuple[list[dict[str, Any]], list[Path]]:
    from binge_schedule.content_catalog import canonical_rows_from_config, write_canonical_catalog

    rows = canonical_rows_from_config(cfg)
    written: list[Path] = []
    for path in catalog_publish_paths():
        write_canonical_catalog(rows, path)
        written.append(path)
    return rows, written


def _show_match_key(name: str) -> str:
    return _normalize_key(name)


def replace_show_catalog_rows(cfg: BuildConfig, display_name: str, incoming: list[dict[str, Any]]) -> dict[str, Any]:
    """Replace all imported catalog rows for one show (spreadsheet save)."""
    show_key = _show_match_key(display_name)
    if not show_key:
        raise ValueError("Show name is required.")
    existing = load_imported_catalog_rows(cfg)
    kept = [
        row
        for row in existing
        if _show_match_key(str(row.get("display_name", ""))) != show_key
        and _show_match_key(str(row.get("series_title", ""))) != show_key
    ]
    normalized: list[dict[str, Any]] = []
    for row in incoming:
        if not isinstance(row, dict):
            continue
        copy = dict(row)
        copy["display_name"] = display_name
        if _normalize_key(copy.get("content_type", "")) != "movie":
            copy["series_title"] = display_name
        normalized.append(copy)
    if not normalized:
        raise ValueError("At least one episode row is required.")
    merged = dedupe_import_rows(kept + normalized)
    save_imported_catalog_rows(cfg, merged)
    catalog_rows, written_paths = publish_content_catalog(cfg)
    return {
        "display_name": display_name,
        "saved_row_count": len(normalized),
        "catalog_row_count": len(catalog_rows),
        "catalog_paths": [path.as_posix() for path in written_paths],
    }


def import_content_rows(cfg: BuildConfig, incoming: list[dict[str, Any]]) -> dict[str, Any]:
    if not incoming:
        raise ValueError("No content rows to import.")
    existing = load_imported_catalog_rows(cfg)
    before = len(existing)
    merged = merge_import_rows(existing, incoming)
    save_imported_catalog_rows(cfg, merged)
    catalog_rows, written_paths = publish_content_catalog(cfg)
    return {
        "imported_count": len(merged) - before,
        "updated_count": max(0, len(incoming) - max(0, len(merged) - before)),
        "total_imported_rows": len(merged),
        "catalog_row_count": len(catalog_rows),
        "catalog_paths": [path.as_posix() for path in written_paths],
    }
