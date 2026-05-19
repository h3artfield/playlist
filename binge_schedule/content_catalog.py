from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from binge_schedule import nikki
from binge_schedule.archive_normalize import season_episode_parts
from binge_schedule.cursor_state import resolved_nikki_workbook_path
from binge_schedule.models import BuildConfig, Episode, NikkiColumnHeaders, ShowDef

CANONICAL_CONTENT_SCHEMA_VERSION = 1


def _clean_text(value: Any) -> str:
    text = " ".join(str(value or "").replace("\xa0", " ").split()).strip()
    return "" if text.casefold() in {"nan", "none", "null", "nat"} else text


def _slug(value: Any, *, fallback: str = "item") -> str:
    text = _clean_text(value).casefold()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or fallback


def _source_file(path: Optional[Path]) -> str:
    return str(path) if path is not None else ""


def _repo_root_for_config(cfg: BuildConfig) -> Path:
    if cfg.config_path is None:
        return Path.cwd()
    config_dir = cfg.config_path.resolve().parent
    return config_dir.parent if config_dir.name.casefold() == "config" else config_dir


def _load_json_map(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _title_keys(title: str) -> list[str]:
    clean = _clean_text(title)
    keys = [clean]
    no_year = re.sub(r"\s*\(\d{4}\)\s*$", "", clean).strip()
    if no_year and no_year != clean:
        keys.append(no_year)
    return [_slug(k) for k in keys if k]


def _lookup_title_value(mapping: dict[str, Any], title: str) -> Any:
    normalized = {_slug(k): v for k, v in mapping.items()}
    for key in _title_keys(title):
        if key in normalized:
            return normalized[key]
    return None


def _content_type_for_show(sd: ShowDef) -> str:
    if sd.kind == "series":
        return "series"
    group = (sd.semantic_group or "").casefold()
    name = sd.display_name.casefold()
    if group == "ministry" or "paid" in name:
        return "paid_programming"
    return "literal"


def _episode_key(series_key: str, ep: Episode, idx0: int) -> str:
    code = _clean_text(ep.code)
    if code:
        return f"{series_key}:{_slug(code)}"
    if ep.episode_num is not None:
        return f"{series_key}:episode-{ep.episode_num}"
    return f"{series_key}:row-{idx0 + 1}"


def _base_row(
    *,
    station_id: str,
    content_type: str,
    series_key: str,
    display_name: str,
    runtime_minutes: Optional[float],
    genre: str,
    semantic_group: str,
    source_file: str,
    source_sheet: str,
    parser_style: str,
    parser_rule: str,
    nikki_row_filter: str,
) -> dict[str, Any]:
    return {
        "schema_version": CANONICAL_CONTENT_SCHEMA_VERSION,
        "station_id": station_id,
        "content_type": content_type,
        "series_key": series_key,
        "display_name": display_name,
        "episode_key": "",
        "episode_code": "",
        "episode_number": "",
        "season_number": None,
        "episode_in_season": None,
        "season_episode": "",
        "episode_title": "",
        "runtime_minutes": runtime_minutes,
        "binge_row_minutes": runtime_minutes,
        "genre": genre,
        "semantic_group": semantic_group,
        "synopsis_short": "",
        "synopsis_long": "",
        "original_airdate": "",
        "production_company": "",
        "copyright": "",
        "availability_status": "available",
        "exclude_reason": "",
        "source_file": source_file,
        "source_sheet": source_sheet,
        "source_row": None,
        "parser_style": parser_style,
        "parser_rule": parser_rule,
        "nikki_row_filter": nikki_row_filter,
        "raw_title": "",
    }


def _show_metadata_row(
    *,
    station_id: str,
    sd: ShowDef,
    workbook_path: Optional[Path],
    availability_status: str,
    exclude_reason: str,
) -> dict[str, Any]:
    style = sd.nikki_style or nikki.default_style_for_sheet(sd.nikki_sheet or sd.display_name)
    row = _base_row(
        station_id=station_id,
        content_type=_content_type_for_show(sd),
        series_key=sd.key,
        display_name=sd.display_name,
        runtime_minutes=sd.binge_row_minutes,
        genre=sd.semantic_group or "",
        semantic_group=sd.semantic_group or "",
        source_file=_source_file(workbook_path),
        source_sheet=sd.nikki_sheet or "",
        parser_style=style,
        parser_rule="yaml_show",
        nikki_row_filter=sd.nikki_row_filter or "",
    )
    row["availability_status"] = availability_status
    row["exclude_reason"] = exclude_reason
    row["episode_key"] = f"{sd.key}:metadata"
    row["episode_title"] = sd.display_name
    return row


def _row_from_episode(
    *,
    station_id: str,
    sd: ShowDef,
    ep: Episode,
    idx0: int,
    workbook_path: Path,
    style: str,
    runtime_minutes: Optional[float] = None,
) -> dict[str, Any]:
    season, ep_in_season = season_episode_parts(ep, style)
    runtime = runtime_minutes if runtime_minutes is not None else sd.binge_row_minutes
    row = _base_row(
        station_id=station_id,
        content_type="series",
        series_key=sd.key,
        display_name=sd.display_name,
        runtime_minutes=runtime,
        genre=sd.semantic_group or "",
        semantic_group=sd.semantic_group or "",
        source_file=str(workbook_path),
        source_sheet=sd.nikki_sheet or "",
        parser_style=style,
        parser_rule="nikki_workbook",
        nikki_row_filter=sd.nikki_row_filter or "",
    )
    row["binge_row_minutes"] = sd.binge_row_minutes
    row.update(
        {
            "episode_key": _episode_key(sd.key, ep, idx0),
            "episode_code": _clean_text(ep.code),
            "episode_number": "" if ep.episode_num is None else str(ep.episode_num),
            "season_number": season,
            "episode_in_season": ep_in_season,
            "season_episode": _clean_text(ep.season_ep or ""),
            "episode_title": _clean_text(ep.title),
            "source_row": idx0 + 1,
            "raw_title": _clean_text(ep.raw),
        }
    )
    return row


def _rows_from_show(
    cfg: BuildConfig,
    sd: ShowDef,
    *,
    station_id: str,
    workbook_path: Path,
) -> list[dict[str, Any]]:
    if sd.kind != "series" or not sd.nikki_sheet:
        return [
            _show_metadata_row(
                station_id=station_id,
                sd=sd,
                workbook_path=workbook_path if str(workbook_path) else None,
                availability_status="available",
                exclude_reason="",
            )
        ]

    style = sd.nikki_style or nikki.default_style_for_sheet(sd.nikki_sheet)
    if not workbook_path.is_file():
        return [
            _show_metadata_row(
                station_id=station_id,
                sd=sd,
                workbook_path=workbook_path,
                availability_status="metadata_only",
                exclude_reason="nikki_workbook_missing",
            )
        ]

    try:
        episodes = nikki.load_sheet(
            str(workbook_path),
            sd.nikki_sheet,
            style=style,
            prefix=sd.prefix,
            columns=nikki.effective_column_headers(sd, style=style),
            row_filter=sd.nikki_row_filter,
        )
    except Exception as exc:
        row = _show_metadata_row(
            station_id=station_id,
            sd=sd,
            workbook_path=workbook_path,
            availability_status="metadata_only",
            exclude_reason=f"load_failed:{type(exc).__name__}",
        )
        return [row]

    if not episodes:
        return [
            _show_metadata_row(
                station_id=station_id,
                sd=sd,
                workbook_path=workbook_path,
                availability_status="metadata_only",
                exclude_reason="no_episodes_loaded",
            )
        ]
    runtime_by_episode = _standard_sheet_runtime_by_episode(
        workbook_path,
        sd.nikki_sheet,
        nikki.effective_column_headers(sd, style=style),
    )
    return [
        _row_from_episode(
            station_id=station_id,
            sd=sd,
            ep=ep,
            idx0=idx0,
            workbook_path=workbook_path,
            style=style,
            runtime_minutes=runtime_by_episode.get(_clean_text(ep.raw)),
        )
        for idx0, ep in enumerate(episodes)
    ]


def _movies_sheet_name(workbook_path: Path) -> Optional[str]:
    if not workbook_path.is_file():
        return None
    try:
        xls = pd.ExcelFile(workbook_path)
    except Exception:
        return None
    for sheet in xls.sheet_names:
        if str(sheet).strip().casefold() == "movies":
            return str(sheet)
    return None


def _movie_rows_from_workbook(
    cfg: BuildConfig,
    *,
    station_id: str,
    workbook_path: Path,
) -> list[dict[str, Any]]:
    sheet = _movies_sheet_name(workbook_path)
    if not sheet:
        return []
    try:
        movies = nikki.load_sheet(
            str(workbook_path),
            sheet,
            style="movies",
            prefix="MOV",
            columns=nikki.effective_column_headers(
                ShowDef(key="movies", display_name="Movies", kind="series", nikki_sheet=sheet, prefix="MOV"),
                style="movies",
            ),
        )
    except Exception:
        return []

    repo_root = _repo_root_for_config(cfg)
    runtime_map = _load_json_map(repo_root / "config" / "movie_runtime_minutes.json")
    genre_map = _load_json_map(repo_root / "config" / "movie_semantic_groups.json")
    rows: list[dict[str, Any]] = []
    for idx0, ep in enumerate(movies):
        title = _clean_text(ep.title)
        if not title:
            continue
        runtime_raw = _lookup_title_value(runtime_map, title)
        try:
            runtime = int(runtime_raw) if runtime_raw not in (None, "") else 120
        except (TypeError, ValueError):
            runtime = 120
        genre = _clean_text(_lookup_title_value(genre_map, title) or "movie")
        row = _base_row(
            station_id=station_id,
            content_type="movie",
            series_key="movies",
            display_name=title,
            runtime_minutes=runtime,
            genre=genre,
            semantic_group=genre,
            source_file=str(workbook_path),
            source_sheet=sheet,
            parser_style="movies",
            parser_rule="nikki_movies_tab",
            nikki_row_filter="",
        )
        row.update(
            {
                "episode_key": f"movies:{_slug(ep.code or title, fallback=f'movie-{idx0 + 1}')}",
                "episode_code": _clean_text(ep.code),
                "episode_number": "" if ep.episode_num is None else str(ep.episode_num),
                "episode_title": title,
                "source_row": idx0 + 1,
                "raw_title": _clean_text(ep.raw),
            }
        )
        rows.append(row)
    return rows


def _workbook_sheet_names(workbook_path: Path) -> list[str]:
    if not workbook_path.is_file():
        return []
    try:
        return [str(s) for s in pd.ExcelFile(workbook_path).sheet_names]
    except Exception:
        return []


def _guess_prefix(sheet_name: str) -> str:
    alnum = re.sub(r"[^A-Za-z0-9]", "", sheet_name)
    return (alnum[:3] or "ZZZ").upper()


def _sheet_key(sheet_name: str) -> str:
    return _clean_text(sheet_name).casefold()


def _synthetic_show_for_sheet(sheet_name: str) -> ShowDef:
    return ShowDef(
        key=f"archive_{_slug(sheet_name)}",
        display_name=_clean_text(sheet_name),
        kind="series",
        nikki_sheet=sheet_name,
        prefix=_guess_prefix(sheet_name),
    )


def _runtime_minutes(value: Any, fallback: float = 30) -> float:
    if value is None:
        return fallback
    if hasattr(value, "hour") and hasattr(value, "minute"):
        try:
            seconds = int(getattr(value, "second", 0) or 0)
            # TRT sheets commonly store MM:SS as an Excel time-of-day value.
            return max(1, round(int(value.hour) + int(value.minute) / 60 + seconds / 3600, 2))
        except Exception:
            return fallback
    if isinstance(value, (int, float)) and not pd.isna(value):
        fv = float(value)
        if 0 < fv < 1:
            return max(1, round(fv * 24 * 60, 2))
        return max(1, round(fv, 2))
    if hasattr(value, "total_seconds"):
        try:
            return max(1, round(float(value.total_seconds()) / 60.0, 2))
        except Exception:
            return fallback
    text = _clean_text(value)
    if not text:
        return fallback
    if text.startswith("0 days "):
        text = text.replace("0 days ", "", 1)
    if ":" in text:
        parts = text.split(":")
        try:
            nums = [int(float(x)) for x in parts]
        except ValueError:
            return fallback
        if len(nums) == 3:
            return max(1, round(nums[0] * 60 + nums[1] + nums[2] / 60, 2))
        if len(nums) == 2:
            a, b = nums
            return max(1, round(a + b / 60, 2))
    try:
        return max(1, round(float(text), 2))
    except ValueError:
        return fallback


def _norm_header(value: Any) -> str:
    return " ".join(str(value).replace("\xa0", " ").split()).casefold()


def _row_header_index_map(row: pd.Series) -> dict[str, int]:
    out: dict[str, int] = {}
    for j in range(len(row)):
        value = row.iloc[j]
        if pd.isna(value):
            continue
        key = _norm_header(value)
        if key and key not in out:
            out[key] = j
    return out


def _find_standard_header_row(df: pd.DataFrame, columns: NikkiColumnHeaders) -> tuple[Optional[int], dict[str, int]]:
    for i in range(min(35, len(df))):
        row = df.iloc[i]
        header_map = _row_header_index_map(row)
        episode_key = _norm_header(columns.episode)
        if episode_key not in header_map:
            continue
        idx = {"episode": header_map[episode_key]}
        for label in ("trt", "runtime", "run time", "total runtime", "duration"):
            if label in header_map:
                idx["runtime"] = header_map[label]
                break
        return i, idx
    return None, {}


def _standard_sheet_runtime_by_episode(
    workbook_path: Path,
    sheet_name: Optional[str],
    columns: NikkiColumnHeaders,
) -> dict[str, int]:
    if not sheet_name:
        return {}
    try:
        df = pd.read_excel(workbook_path, sheet_name=sheet_name, header=None)
    except Exception:
        return {}
    header_row, col_idx = _find_standard_header_row(df, columns)
    ep_col = col_idx.get("episode")
    runtime_col = col_idx.get("runtime")
    if header_row is None or ep_col is None or runtime_col is None:
        return {}
    out: dict[str, int] = {}
    for i in range(header_row + 1, len(df)):
        episode = _clean_text(df.iloc[i, ep_col] if ep_col < len(df.columns) else "")
        if not episode or _norm_header(episode) == _norm_header(columns.episode):
            continue
        runtime = _runtime_minutes(df.iloc[i, runtime_col] if runtime_col < len(df.columns) else None, fallback=0)
        if runtime > 0:
            out.setdefault(episode, runtime)
    return out


def _split_new_shows_display(title: str, fallback: str) -> str:
    if " — " in title:
        return _clean_text(title.split(" — ", 1)[0]) or fallback
    return fallback


def _row_from_archive_episode(
    *,
    station_id: str,
    sd: ShowDef,
    ep: Episode,
    idx0: int,
    workbook_path: Path,
    style: str,
    runtime_minutes: float,
    display_name: Optional[str] = None,
    parser_rule: str = "archive_workbook_tab",
    synopsis_short: str = "",
    scheduled_minutes: Optional[float] = None,
) -> dict[str, Any]:
    row = _row_from_episode(
        station_id=station_id,
        sd=sd,
        ep=ep,
        idx0=idx0,
        workbook_path=workbook_path,
        style=style,
    )
    display = display_name or sd.display_name
    row.update(
        {
            "series_key": f"archive_{_slug(display)}",
            "display_name": display,
            "runtime_minutes": runtime_minutes,
            "binge_row_minutes": scheduled_minutes if scheduled_minutes is not None else runtime_minutes,
            "source_sheet": sd.nikki_sheet or "",
            "parser_rule": parser_rule,
            "synopsis_short": synopsis_short,
            "episode_key": f"archive_{_slug(display)}:{_slug(ep.code or ep.title, fallback=f'row-{idx0 + 1}')}",
        }
    )
    return row


def _headerless_archive_rows(
    *,
    station_id: str,
    workbook_path: Path,
    sheet_name: str,
    title_prefix_to_remove: str = "",
    runtime_col: Optional[int] = None,
    season_ep_col: Optional[int] = None,
    synopsis_col: Optional[int] = None,
) -> list[dict[str, Any]]:
    try:
        df = pd.read_excel(workbook_path, sheet_name=sheet_name, header=None)
    except Exception:
        return []
    sd = _synthetic_show_for_sheet(sheet_name)
    rows: list[dict[str, Any]] = []
    for i, r in df.iterrows():
        title = _clean_text(r.iloc[0] if len(r) > 0 else "")
        if not title:
            continue
        if title_prefix_to_remove and title.casefold() == title_prefix_to_remove.casefold():
            continue
        if title_prefix_to_remove and title.casefold().startswith(f"{title_prefix_to_remove.casefold()}:"):
            title = _clean_text(title.split(":", 1)[1])
        if title.casefold().startswith("season "):
            continue
        runtime = _runtime_minutes(
            r.iloc[runtime_col] if runtime_col is not None and len(r) > runtime_col else None,
            fallback=sd.binge_row_minutes,
        )
        season_ep = _clean_text(r.iloc[season_ep_col] if season_ep_col is not None and len(r) > season_ep_col else "")
        synopsis = _clean_text(r.iloc[synopsis_col] if synopsis_col is not None and len(r) > synopsis_col else "")
        ep = Episode(
            raw=title,
            title=title,
            code=f"{sd.prefix}{len(rows) + 1}",
            episode_num=len(rows) + 1,
            season_ep=season_ep or None,
        )
        rows.append(
            _row_from_archive_episode(
                station_id=station_id,
                sd=sd,
                ep=ep,
                idx0=len(rows),
                workbook_path=workbook_path,
                style="headerless",
                runtime_minutes=runtime,
                parser_rule="archive_headerless_tab",
                synopsis_short=synopsis,
            )
        )
    return rows


def _standard_archive_rows(
    *,
    station_id: str,
    workbook_path: Path,
    sheet_name: str,
) -> list[dict[str, Any]]:
    sd = _synthetic_show_for_sheet(sheet_name)
    style = nikki.default_style_for_sheet(sheet_name)
    header_variants = [
        nikki.effective_column_headers(sd, style=style),
        NikkiColumnHeaders(episode="Episode", season_episode=None, year=None, stars="Stars", synopsis="Synopsis"),
    ]
    episodes: list[Episode] = []
    for columns in header_variants:
        try:
            episodes = nikki.load_sheet(
                str(workbook_path),
                sheet_name,
                style=style,
                prefix=sd.prefix,
                columns=columns,
            )
        except Exception:
            episodes = []
        if episodes:
            break
    if not episodes:
        if sheet_name == "Stingray":
            return _headerless_archive_rows(
                station_id=station_id,
                workbook_path=workbook_path,
                sheet_name=sheet_name,
                runtime_col=1,
                season_ep_col=2,
                synopsis_col=3,
            )
        if sheet_name == "FARSCAPE":
            return _headerless_archive_rows(
                station_id=station_id,
                workbook_path=workbook_path,
                sheet_name=sheet_name,
                title_prefix_to_remove="Farscape",
                synopsis_col=1,
            )
        return []
    runtime_by_episode = _standard_sheet_runtime_by_episode(
        workbook_path,
        sheet_name,
        nikki.effective_column_headers(sd, style=style),
    )
    runtime = 60 if any(token in sheet_name.casefold() for token in ("commish", "farscape", "silk", "wiseguy")) else sd.binge_row_minutes
    out: list[dict[str, Any]] = []
    for idx0, ep in enumerate(episodes):
        display = _split_new_shows_display(ep.title, sd.display_name) if sheet_name == "NEW SHOWS" else sd.display_name
        episode_runtime = runtime_by_episode.get(_clean_text(ep.raw), runtime)
        out.append(
            _row_from_archive_episode(
                station_id=station_id,
                sd=sd,
                ep=ep,
                idx0=idx0,
                workbook_path=workbook_path,
                style=style,
                runtime_minutes=episode_runtime,
                scheduled_minutes=runtime,
                display_name=display,
            )
        )
    return out


def _unconfigured_archive_rows(
    cfg: BuildConfig,
    *,
    station_id: str,
    workbook_path: Path,
) -> list[dict[str, Any]]:
    used = {_sheet_key(sd.nikki_sheet or "") for sd in cfg.shows.values() if sd.kind == "series" and sd.nikki_sheet}
    rows: list[dict[str, Any]] = []
    for sheet_name in _workbook_sheet_names(workbook_path):
        if _sheet_key(sheet_name) in used or _sheet_key(sheet_name) == "movies":
            continue
        rows.extend(_standard_archive_rows(station_id=station_id, workbook_path=workbook_path, sheet_name=sheet_name))
    return rows


def canonical_rows_from_config(cfg: BuildConfig, *, station_id: Optional[str] = None) -> list[dict[str, Any]]:
    """Normalize YAML/Nikki content rules into the shared content table."""
    sid = station_id or (cfg.config_path.stem if cfg.config_path else "default")
    workbook_path = resolved_nikki_workbook_path(cfg)
    rows: list[dict[str, Any]] = []
    for key in sorted(cfg.shows):
        rows.extend(_rows_from_show(cfg, cfg.shows[key], station_id=sid, workbook_path=workbook_path))
    rows.extend(_unconfigured_archive_rows(cfg, station_id=sid, workbook_path=workbook_path))
    rows.extend(_movie_rows_from_workbook(cfg, station_id=sid, workbook_path=workbook_path))
    return rows


def _content_type_from_imported(value: Any) -> str:
    raw = _clean_text(value).casefold().replace(" ", "_")
    if raw in {"movie", "movies", "special", "specials", "film", "feature", "movie/special"}:
        return "movie"
    if raw in {"paid", "paid_programming", "infomercial", "ministry"}:
        return "paid_programming"
    if raw in {"literal", "program", "block"}:
        return "literal"
    return "series"


def canonical_rows_from_imported_rows(
    imported_rows: list[dict[str, Any]],
    *,
    station_id: str,
) -> list[dict[str, Any]]:
    """Normalize uploaded-content rows into the same schema as YAML/Nikki content."""
    rows: list[dict[str, Any]] = []
    for idx0, src in enumerate(imported_rows):
        content_type = _content_type_from_imported(src.get("content_type", "series"))
        display = _clean_text(src.get("display_name")) or _clean_text(src.get("series_title"))
        if not display:
            continue
        series_key = _slug(src.get("series_title") or display, fallback=f"content-{idx0 + 1}")
        ep_num = _clean_text(src.get("episode_number"))
        ep_title = _clean_text(src.get("episode_title")) or (display if content_type != "series" else "")
        runtime = src.get("runtime_minutes")
        try:
            runtime_minutes = int(runtime) if runtime not in (None, "") else None
        except (TypeError, ValueError):
            runtime_minutes = None
        row = _base_row(
            station_id=station_id,
            content_type=content_type,
            series_key=series_key,
            display_name=display,
            runtime_minutes=runtime_minutes,
            genre=_clean_text(src.get("genre")).casefold(),
            semantic_group=_clean_text(src.get("genre")).casefold(),
            source_file=_clean_text(src.get("source_file")),
            source_sheet=_clean_text(src.get("source_sheet")),
            parser_style="uploaded_mapping",
            parser_rule="uploaded_content",
            nikki_row_filter="",
        )
        token = ep_num or ep_title or display
        row.update(
            {
                "episode_key": f"{series_key}:{_slug(token, fallback=f'row-{idx0 + 1}')}",
                "episode_code": _clean_text(src.get("episode_code")),
                "episode_number": ep_num,
                "episode_title": ep_title,
                "synopsis_short": _clean_text(src.get("synopsis_short")),
                "synopsis_long": _clean_text(src.get("synopsis_long")),
                "original_airdate": _clean_text(src.get("original_airdate")),
                "production_company": _clean_text(src.get("production_company")),
                "copyright": _clean_text(src.get("copyright")),
                "source_row": idx0 + 1,
                "raw_title": ep_title or display,
            }
        )
        rows.append(row)
    return rows


def write_canonical_catalog(rows: list[dict[str, Any]], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": CANONICAL_CONTENT_SCHEMA_VERSION,
        "row_count": len(rows),
        "rows": rows,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path
