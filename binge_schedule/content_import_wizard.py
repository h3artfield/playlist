from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Literal, Optional

import pandas as pd

from binge_schedule.content_import import import_content_rows, import_row_identity_key, parse_playable_cell, parse_slot_minutes_cell

MatchQuality = Literal["exact", "likely", "manual", "unmapped", "inferred"]
RowKind = Literal["auto", "series", "movie"]

CANONICAL_FIELDS: list[dict[str, Any]] = [
    {"key": "title", "label": "Episode or movie title", "required": True},
    {"key": "series_title", "label": "Series / show", "required": False},
    {"key": "episode_number", "label": "Episode number", "required": False},
    {"key": "playable", "label": "Playable (Yes/No)", "required": False},
    {"key": "runtime", "label": "Runtime (TRT)", "required": False},
    {"key": "slot", "label": "Grid slot (30/60/120)", "required": False},
    {"key": "genre", "label": "Genre", "required": False},
    {"key": "original_airdate", "label": "Original airdate / year", "required": False},
    {"key": "content_type", "label": "Content type", "required": False},
    {"key": "synopsis_short", "label": "Short synopsis", "required": False},
    {"key": "synopsis_long", "label": "Long synopsis", "required": False},
    {"key": "copyright", "label": "Copyright", "required": False},
]

IMPORT_ALIASES: dict[str, set[str]] = {
    "series_title": {
        "series title",
        "series name",
        "series",
        "artist/series",
        "show",
        "show title",
        "program",
        "program title",
        "program name",
    },
    "title": {
        "title",
        "episode",
        "episode title",
        "episode name",
        "asset title",
        "movie title",
        "title (internal)",
        "sort title",
    },
    "episode_number": {
        "episode number",
        "season/episode",
        "season_episode",
        "ep #",
        "episode #",
    },
    "synopsis_short": {
        "episode short synopsis",
        "short description",
        "series short synopsis (150 characters)",
        "synopsis short",
    },
    "synopsis_long": {
        "episode long synopsis",
        "description",
        "synopsis",
        "series long synopsis (250 characters)",
        "synopsis long",
    },
    "original_airdate": {
        "original airdate",
        "year/original airdate",
        "air date",
        "production year",
        "year",
    },
    "runtime": {
        "runtime",
        "trt",
        "rt",
        "duration",
        "running time",
        "length",
        "run time",
        "run time (min)",
    },
    "slot": {
        "slot",
        "grid slot",
        "slot length",
        "binge slot",
        "block length",
    },
    "genre": {
        "genre",
        "amazon channels genre",
        "roku genre tags",
        "category",
    },
    "copyright": {"copyright"},
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
    "content_type": {
        "content type",
        "type",
        "format",
        "asset type",
        "program type",
        "category",
    },
}

_SESSION_TTL_SECONDS = 30 * 60
_IMPORT_SESSIONS: dict[str, dict[str, Any]] = {}

_RUNTIME_TEXT_RE = re.compile(r"^\d{1,2}:\d{2}(?::\d{2})?$")
_EPISODE_CODE_RE = re.compile(r"^(?:s\d+e\d+|\d{1,2}_\d{1,2})$", re.IGNORECASE)

# Friendly header labels when columns are inferred from data (no header row).
INFERRED_COLUMN_LABELS: dict[str, str] = {
    "title": "Episode",
    "series_title": "Series",
    "episode_number": "Season/Episode",
    "runtime": "TRT",
    "slot": "Slot",
    "synopsis_long": "Synopsis",
    "synopsis_short": "Short Synopsis",
    "original_airdate": "Year/Original Airdate",
    "genre": "Genre",
    "content_type": "Content Type",
    "copyright": "Copyright",
    "playable": "Playable",
}


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


def _alias_flat() -> set[str]:
    return {alias for aliases in IMPORT_ALIASES.values() for alias in aliases}


def detect_header_row(df_raw: pd.DataFrame) -> int:
    alias_flat = _alias_flat()
    best_row = 0
    best_score = -1
    for hdr in range(min(15, len(df_raw))):
        vals = [_normalize_key(v) for v in list(df_raw.iloc[hdr].values)]
        score = sum(1 for v in vals if v in alias_flat)
        non_empty = sum(1 for v in vals if v)
        if score > best_score or (score == best_score and non_empty > 0 and hdr == 0):
            best_score = score
            best_row = hdr
    return best_row


def dataframe_from_header_row(df_raw: pd.DataFrame, header_row: int) -> pd.DataFrame:
    header_vals = [
        _clean_text(v) if _clean_text(v) else f"col_{i}"
        for i, v in enumerate(list(df_raw.iloc[int(header_row)].values))
    ]
    data = df_raw.iloc[int(header_row) + 1 :].copy()
    data.columns = header_vals
    return data.dropna(how="all")


def guess_column(columns: list[str], canon: str) -> tuple[str, MatchQuality]:
    aliases = IMPORT_ALIASES.get(canon, set())
    for column in columns:
        if _normalize_key(column) in aliases:
            return column, "exact"
    canon_norm = _normalize_key(canon.replace("_", " "))
    for column in columns:
        col_norm = _normalize_key(column)
        if canon_norm and (canon_norm in col_norm or col_norm in canon_norm):
            return column, "likely"
    return "", "unmapped"


def suggest_mapping(columns: list[str]) -> tuple[dict[str, str], dict[str, MatchQuality]]:
    mapping: dict[str, str] = {}
    match: dict[str, MatchQuality] = {}
    used_columns: set[str] = set()
    for field in CANONICAL_FIELDS:
        key = str(field["key"])
        column, quality = guess_column(columns, key)
        if column and column in used_columns:
            column, quality = "", "unmapped"
        if column:
            used_columns.add(column)
        mapping[key] = column
        match[key] = quality
    title_col = mapping.get("title", "")
    if title_col and mapping.get("series_title") == title_col:
        mapping["series_title"] = ""
        match["series_title"] = "unmapped"
    return mapping, match


def suggest_row_kind(sheet_name: str, mapping: dict[str, str], columns: list[str]) -> RowKind:
    name = sheet_name.strip().lower()
    if name in {"movies", "movie", "films", "features"}:
        return "movie"
    if mapping.get("series_title") and not mapping.get("episode_number"):
        return "movie"
    if mapping.get("episode_number") or mapping.get("series_title"):
        return "series"
    if "movie" in name or "film" in name:
        return "movie"
    return "auto"


def sheet_header_score(df_raw: pd.DataFrame, header_row: int) -> int:
    if header_row >= len(df_raw):
        return 0
    vals = [_normalize_key(v) for v in list(df_raw.iloc[header_row].values)]
    return sum(1 for v in vals if v in _alias_flat())


def _looks_like_runtime(value: Any) -> bool:
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except Exception:
        pass
    if hasattr(value, "total_seconds"):
        try:
            seconds = float(value.total_seconds())
            return 60 <= seconds <= 6 * 3600
        except Exception:
            pass
    text = _clean_text(value)
    if not text:
        return False
    if _looks_like_episode_code(text):
        return False
    if _RUNTIME_TEXT_RE.match(text.strip()):
        return True
    return _runtime_minutes_from_cell(value) is not None


def _looks_like_episode_code(text: str) -> bool:
    compact = re.sub(r"\s+", "", text.strip().lower())
    if not compact or compact in {"n/a", "na", "-"}:
        return False
    return bool(_EPISODE_CODE_RE.match(compact))


def _looks_like_date(text: str) -> bool:
    if not text:
        return False
    try:
        parsed = pd.to_datetime(text, errors="coerce")
        return bool(pd.notna(parsed))
    except Exception:
        return False


def _looks_like_synopsis(text: str) -> bool:
    return len(text) >= 45


def _looks_like_title(text: str) -> bool:
    if not text or len(text) < 2:
        return False
    if _looks_like_runtime(text) or _looks_like_episode_code(text):
        return False
    if _looks_like_date(text) and len(text) < 30:
        return False
    return len(text) <= 180


def _row_data_likelihood(row_values: list[Any]) -> int:
    texts = [_clean_text(v) for v in row_values if _clean_text(v)]
    score = 0
    if sum(1 for v in texts if _looks_like_title(v)) >= 1:
        score += 2
    if sum(1 for v in row_values if _looks_like_runtime(v)) >= 1:
        score += 2
    if sum(1 for v in texts if _looks_like_episode_code(v)) >= 1:
        score += 1
    if sum(1 for v in texts if _looks_like_synopsis(v)) >= 1:
        score += 1
    return score


def find_first_data_row(df_raw: pd.DataFrame) -> int:
    best_row = 0
    best_score = -1
    for row_idx in range(min(20, len(df_raw))):
        vals = [_clean_text(v) for v in list(df_raw.iloc[row_idx].values)]
        non_empty = [v for v in vals if v]
        if len(non_empty) < 2:
            continue
        alias_hits = sum(1 for v in (_normalize_key(x) for x in non_empty) if v in _alias_flat())
        if alias_hits >= 2:
            return row_idx
        data_score = _row_data_likelihood(list(df_raw.iloc[row_idx].values))
        if data_score > best_score:
            best_score = data_score
            best_row = row_idx
    return best_row


def _profile_column(series: pd.Series) -> dict[str, float]:
    raw = [v for v in series.head(25) if v is not None and _clean_text(v)]
    if not raw:
        try:
            raw = [v for v in series.head(25) if v is not None and not (isinstance(v, float) and pd.isna(v))]
        except Exception:
            raw = [v for v in series.head(25) if v is not None]
    if not raw:
        return {}
    total = len(raw)
    texts = [_clean_text(v) for v in raw]
    return {
        "title": sum(1 for s in texts if _looks_like_title(s)) / total,
        "runtime": sum(1 for v in raw if _looks_like_runtime(v)) / total,
        "episode_number": sum(1 for s in texts if _looks_like_episode_code(s)) / total,
        "synopsis_long": sum(1 for s in texts if _looks_like_synopsis(s)) / total,
        "original_airdate": sum(1 for s in texts if _looks_like_date(s)) / total,
        "genre": sum(1 for s in texts if 2 < len(s) <= 40 and "," not in s and not _looks_like_title(s)) / total,
    }


def infer_column_roles(df_raw: pd.DataFrame, data_start_row: int) -> dict[int, str]:
    slice_df = df_raw.iloc[data_start_row : data_start_row + 30]
    if slice_df.empty:
        return {}
    col_count = slice_df.shape[1]
    profiles = [_profile_column(slice_df.iloc[:, col_idx]) for col_idx in range(col_count)]
    assignments: dict[int, str] = {}
    used: set[int] = set()
    priority = [
        "title",
        "episode_number",
        "runtime",
        "synopsis_long",
        "original_airdate",
        "genre",
        "series_title",
        "synopsis_short",
    ]
    thresholds = {
        "title": 0.2,
        "episode_number": 0.15,
        "runtime": 0.15,
        "synopsis_long": 0.15,
    }
    for field in priority:
        best_col = -1
        best_val = -1.0
        for col_idx, profile in enumerate(profiles):
            if col_idx in used:
                continue
            val = profile.get(field, 0.0)
            if val > best_val:
                best_val = val
                best_col = col_idx
        if best_col < 0 or best_val < thresholds.get(field, 0.12):
            continue
        assignments[best_col] = field
        used.add(best_col)
    return assignments


def build_inferred_dataframe(df_raw: pd.DataFrame, data_start_row: int, column_labels: list[str]) -> pd.DataFrame:
    data = df_raw.iloc[int(data_start_row) :].copy()
    width = data.shape[1]
    labels = list(column_labels[:width])
    if len(labels) < width:
        labels.extend(f"col_{i}" for i in range(len(labels), width))
    data.columns = labels
    return data.dropna(how="all")


def load_raw_sheets(filename: str, payload: bytes) -> dict[str, pd.DataFrame]:
    name = str(filename or "").strip()
    lower = name.lower()
    if lower.endswith(".csv"):
        return {"CSV": pd.read_csv(BytesIO(payload), header=None)}
    workbook = pd.ExcelFile(BytesIO(payload))
    sheets: dict[str, pd.DataFrame] = {}
    for sheet_name in workbook.sheet_names:
        sheets[sheet_name] = pd.read_excel(BytesIO(payload), sheet_name=sheet_name, header=None)
    return sheets


def _purge_expired_sessions() -> None:
    now = time.time()
    expired = [sid for sid, data in _IMPORT_SESSIONS.items() if now - data.get("created_at", 0) > _SESSION_TTL_SECONDS]
    for sid in expired:
        _IMPORT_SESSIONS.pop(sid, None)


def create_import_session(filename: str, payload: bytes) -> str:
    if not payload:
        raise ValueError("Uploaded file is empty.")
    lower = str(filename or "").lower()
    if not lower.endswith((".csv", ".xlsx", ".xls")):
        raise ValueError("Upload a CSV or Excel (.csv, .xlsx, .xls) file.")
    _purge_expired_sessions()
    session_id = str(uuid.uuid4())
    sheets = load_raw_sheets(filename, payload)
    _IMPORT_SESSIONS[session_id] = {
        "session_id": session_id,
        "filename": filename,
        "payload": payload,
        "sheets": sheets,
        "created_at": time.time(),
    }
    return session_id


def get_import_session(session_id: str) -> dict[str, Any]:
    _purge_expired_sessions()
    session = _IMPORT_SESSIONS.get(session_id)
    if session is None:
        raise ValueError("Import session expired or not found. Upload the file again.")
    return session


@dataclass
class SheetImportConfig:
    sheet_name: str
    include: bool = True
    header_row: int = 1
    row_kind: RowKind = "auto"
    default_series_title: str = ""
    mapping: dict[str, str] | None = None
    layout: str = "header"
    data_start_row: int = 1
    inferred_column_names: list[str] | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> SheetImportConfig:
        mapping = raw.get("mapping")
        inferred = raw.get("inferred_column_names")
        return cls(
            sheet_name=str(raw.get("sheet_name", "")),
            include=bool(raw.get("include", True)),
            header_row=int(raw.get("header_row", 1) or 0),
            row_kind=str(raw.get("row_kind", "auto")),  # type: ignore[arg-type]
            default_series_title=str(raw.get("default_series_title", "") or ""),
            mapping=dict(mapping) if isinstance(mapping, dict) else {},
            layout=str(raw.get("layout", "header") or "header"),
            data_start_row=max(1, int(raw.get("data_start_row", 1) or 1)),
            inferred_column_names=list(inferred) if isinstance(inferred, list) else None,
        )


def build_sheet_dataframe(df_raw: pd.DataFrame, config: SheetImportConfig) -> pd.DataFrame:
    if config.layout == "inferred" or config.header_row <= 0:
        labels = config.inferred_column_names or []
        if not labels and config.mapping:
            labels = [str(v) for v in config.mapping.values() if v]
        start = max(0, config.data_start_row - 1)
        return build_inferred_dataframe(df_raw, start, labels)
    header_row = max(0, config.header_row - 1)
    return dataframe_from_header_row(df_raw, header_row)


def _apply_inferred_match_quality(
    mapping: dict[str, str],
    match: dict[str, MatchQuality],
    roles: dict[int, str],
    column_labels: list[str],
) -> dict[str, MatchQuality]:
    label_to_field = {column_labels[idx]: field for idx, field in roles.items() if idx < len(column_labels)}
    updated = dict(match)
    for field, column in mapping.items():
        if column and label_to_field.get(column) == field:
            updated[field] = "inferred"
    return updated


def analyze_sheet_inferred(sheet_name: str, df_raw: pd.DataFrame, data_start_row: int) -> dict[str, Any]:
    roles = infer_column_roles(df_raw, data_start_row)
    col_count = int(df_raw.shape[1]) if not df_raw.empty else 0
    column_labels = [
        INFERRED_COLUMN_LABELS.get(roles[i], f"col_{i}") if i in roles else f"col_{i}"
        for i in range(col_count)
    ]
    norm = build_inferred_dataframe(df_raw, data_start_row, column_labels)
    columns = [str(c) for c in norm.columns]
    mapping, match = suggest_mapping(columns)
    match = _apply_inferred_match_quality(mapping, match, roles, column_labels)
    row_kind = suggest_row_kind(sheet_name, mapping, columns)
    data_rows = len(norm)
    include = bool(mapping.get("title")) and data_rows > 0
    skip_reason = ""
    if not include:
        if data_rows == 0:
            skip_reason = "No data rows"
        else:
            skip_reason = "Could not infer episode/movie title column"
    return {
        "name": sheet_name,
        "row_count": len(df_raw),
        "data_row_count": data_rows,
        "column_count": len(columns),
        "header_row": 0,
        "header_score": 0,
        "layout": "inferred",
        "data_start_row": data_start_row + 1,
        "inferred_column_names": column_labels,
        "source_columns": columns,
        "suggested_mapping": mapping,
        "mapping_match": match,
        "suggested_row_kind": row_kind,
        "default_series_title": sheet_name.strip() if row_kind in {"series", "auto"} else "",
        "include": include,
        "skip_reason": skip_reason,
    }


def analyze_sheet_at_header(sheet_name: str, df_raw: pd.DataFrame, header_row: int) -> dict[str, Any]:
    header_row = max(0, min(int(header_row), max(0, len(df_raw) - 1)))
    score = sheet_header_score(df_raw, header_row)
    norm = dataframe_from_header_row(df_raw, header_row)
    columns = [str(c) for c in norm.columns]
    mapping, match = suggest_mapping(columns)
    row_kind = suggest_row_kind(sheet_name, mapping, columns)
    data_rows = len(norm)
    include = score >= 1 and data_rows > 0
    skip_reason = ""
    if not include:
        if data_rows == 0:
            skip_reason = "No data rows"
        elif score == 0:
            skip_reason = "No recognizable column headers"
    return {
        "name": sheet_name,
        "row_count": len(df_raw),
        "data_row_count": data_rows,
        "column_count": len(columns),
        "header_row": header_row + 1,
        "header_score": score,
        "layout": "header",
        "data_start_row": header_row + 2,
        "inferred_column_names": [],
        "source_columns": columns,
        "suggested_mapping": mapping,
        "mapping_match": match,
        "suggested_row_kind": row_kind,
        "default_series_title": sheet_name.strip() if row_kind in {"series", "auto"} else "",
        "include": include,
        "skip_reason": skip_reason,
    }


def analyze_sheet(sheet_name: str, df_raw: pd.DataFrame) -> dict[str, Any]:
    header_row = detect_header_row(df_raw)
    score = sheet_header_score(df_raw, header_row)
    if score >= 1:
        return analyze_sheet_at_header(sheet_name, df_raw, header_row)
    data_start = find_first_data_row(df_raw)
    if sheet_header_score(df_raw, data_start) >= 2:
        return analyze_sheet_at_header(sheet_name, df_raw, data_start)
    inferred = analyze_sheet_inferred(sheet_name, df_raw, data_start)
    if inferred.get("include"):
        return inferred
    return analyze_sheet_at_header(sheet_name, df_raw, header_row)


def analyze_sheet_in_session(session_id: str, sheet_name: str, header_row: int) -> dict[str, Any]:
    session = get_import_session(session_id)
    df_raw = session["sheets"].get(sheet_name)
    if df_raw is None:
        raise ValueError(f"Sheet not found: {sheet_name}")
    if int(header_row) <= 0:
        data_start = find_first_data_row(df_raw)
        analysis = analyze_sheet_inferred(sheet_name, df_raw, data_start)
    else:
        analysis = analyze_sheet_at_header(sheet_name, df_raw, max(0, int(header_row) - 1))
    analysis["sample_rows"] = sample_rows_for_analysis(
        df_raw,
        sheet_name,
        str(session["filename"]),
        analysis,
    )
    analysis["mapping_summary"] = [
        {"field": field["label"], "column": analysis["suggested_mapping"].get(field["key"], "")}
        for field in CANONICAL_FIELDS
        if analysis["suggested_mapping"].get(field["key"])
    ]
    return analysis


def sample_rows_for_analysis(
    df_raw: pd.DataFrame,
    sheet_name: str,
    source_name: str,
    analysis: dict[str, Any],
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    if not analysis.get("suggested_mapping", {}).get("title"):
        return []
    config = SheetImportConfig(
        sheet_name=sheet_name,
        include=True,
        header_row=int(analysis["header_row"]),
        row_kind=str(analysis.get("suggested_row_kind", "auto")),  # type: ignore[arg-type]
        default_series_title=str(analysis.get("default_series_title", "")),
        mapping=dict(analysis.get("suggested_mapping", {})),
        layout=str(analysis.get("layout", "header")),
        data_start_row=int(analysis.get("data_start_row", 1) or 1),
        inferred_column_names=list(analysis.get("inferred_column_names") or []),
    )
    norm = build_sheet_dataframe(df_raw, config)
    rows, _ = rows_from_sheet(
        norm,
        sheet_name=sheet_name,
        source_name=source_name,
        config=config,
    )
    return rows[:limit]


def parse_session_response(session_id: str) -> dict[str, Any]:
    session = get_import_session(session_id)
    source_name = str(session["filename"])
    sheets_out = []
    for sheet_name, df_raw in session["sheets"].items():
        analysis = analyze_sheet(sheet_name, df_raw)
        analysis["sample_rows"] = sample_rows_for_analysis(df_raw, sheet_name, source_name, analysis)
        mapped = [
            {"field": field["label"], "column": analysis["suggested_mapping"].get(field["key"], "")}
            for field in CANONICAL_FIELDS
            if analysis["suggested_mapping"].get(field["key"])
        ]
        analysis["mapping_summary"] = mapped
        sheets_out.append(analysis)
    return {
        "session_id": session_id,
        "filename": session["filename"],
        "fields": CANONICAL_FIELDS,
        "sheets": sheets_out,
    }


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
    if hasattr(value, "total_seconds"):
        try:
            return max(1, int(round(float(value.total_seconds()) / 60.0)))
        except Exception:
            return None
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
            return max(1, nums[0] * 60 + nums[1])
        if len(nums) == 2:
            a, b = nums
            if a >= 10:
                return max(1, int(round(a + b / 60)))
            return max(1, int(round(a * 60 + b)))
    try:
        return max(1, int(round(float(text))))
    except ValueError:
        return None


def rows_from_sheet(
    df: pd.DataFrame,
    *,
    sheet_name: str,
    source_name: str,
    config: SheetImportConfig,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    mapping = config.mapping or {}
    issues: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []

    def cell(record: pd.Series, canon: str) -> Any:
        column = mapping.get(canon, "")
        if not column:
            return None
        return record.get(column, None)

    title_col = mapping.get("title", "")
    if not title_col:
        issues.append({"sheet": sheet_name, "row": None, "level": "error", "message": "Episode or movie title is not mapped."})
        return rows, issues

    default_series = config.default_series_title.strip()
    for row_index, record in df.iterrows():
        if config.layout == "inferred" or config.header_row <= 0:
            excel_row = int(row_index) + int(config.data_start_row) + 1
        else:
            excel_row = int(row_index) + int(config.header_row) + 2
        series_title = _clean_text(cell(record, "series_title")) or default_series
        title = _clean_text(cell(record, "title"))
        ep_num = _clean_text(cell(record, "episode_number"))
        raw_type = _clean_text(cell(record, "content_type")).lower()

        if config.row_kind == "series":
            is_series = True
        elif config.row_kind == "movie":
            is_series = False
        elif raw_type:
            is_series = raw_type not in {"movie", "movies", "special", "specials", "film", "feature"}
        else:
            same_title_column = bool(
                mapping.get("title")
                and mapping.get("series_title") == mapping.get("title")
            )
            if same_title_column and not ep_num:
                is_series = False
            else:
                is_series = bool(series_title and (ep_num or title))

        if is_series and not series_title:
            series_title = sheet_name.strip()

        display = series_title if is_series else title
        if not display:
            issues.append(
                {
                    "sheet": sheet_name,
                    "row": excel_row,
                    "level": "skipped",
                    "message": "Missing show or title.",
                }
            )
            continue

        if is_series and not title and not ep_num:
            issues.append(
                {
                    "sheet": sheet_name,
                    "row": excel_row,
                    "level": "warning",
                    "message": "Series row has no episode number or title.",
                }
            )

        runtime = _runtime_minutes_from_cell(cell(record, "runtime"))
        if cell(record, "runtime") is not None and _clean_text(cell(record, "runtime")) and runtime is None:
            issues.append(
                {
                    "sheet": sheet_name,
                    "row": excel_row,
                    "level": "warning",
                    "message": "Could not parse runtime.",
                }
            )

        air_raw = cell(record, "original_airdate")
        air_iso = ""
        try:
            if pd.notna(air_raw):
                air_iso = pd.to_datetime(air_raw).date().isoformat()
        except Exception:
            air_iso = _clean_text(air_raw)

        playable_col = mapping.get("playable", "")
        if playable_col:
            playable = parse_playable_cell(cell(record, "playable"))
        else:
            playable = True

        slot_minutes = None
        is_movie_row = not is_series
        if not is_movie_row:
            slot_raw = cell(record, "slot")
            slot_minutes = parse_slot_minutes_cell(slot_raw)
            if slot_raw is not None and _clean_text(slot_raw) and slot_minutes is None:
                issues.append(
                    {
                        "sheet": sheet_name,
                        "row": excel_row,
                        "level": "warning",
                        "message": "Slot must be 30, 60, or 120 (series and paid programming only).",
                    }
                )

        rows.append(
            {
                "content_type": "series" if is_series else "movie",
                "display_name": display,
                "series_title": series_title if is_series else "",
                "episode_number": ep_num if is_series else "",
                "episode_title": title if is_series else "",
                "genre": _clean_text(cell(record, "genre")).split(",")[0].strip().lower(),
                "runtime_minutes": runtime,
                "slot_minutes": slot_minutes,
                "original_airdate": air_iso,
                "copyright": _clean_text(cell(record, "copyright")),
                "synopsis_short": _clean_text(cell(record, "synopsis_short")),
                "synopsis_long": _clean_text(cell(record, "synopsis_long")),
                "playable": playable,
                "source_sheet": sheet_name,
                "source_file": source_name,
            }
        )
    return rows, issues


def _catalog_row_as_import(row: dict[str, Any]) -> dict[str, Any]:
    raw_type = _normalize_key(row.get("content_type", ""))
    display = _clean_text(row.get("display_name", ""))
    is_series = raw_type == "series" or (raw_type not in {"movie", "movies", "paid_programming", "literal"} and bool(
        _clean_text(row.get("episode_number", "")) or _clean_text(row.get("episode_title", ""))
    ))
    if is_series:
        return {
            "content_type": "series",
            "display_name": display,
            "series_title": display,
            "episode_number": _clean_text(row.get("episode_number", "")),
            "episode_title": _clean_text(row.get("episode_title", "")),
        }
    return {
        "content_type": raw_type or "movie",
        "display_name": display,
        "series_title": "",
        "episode_number": "",
        "episode_title": _clean_text(row.get("episode_title", "")) or display,
    }


def build_catalog_index(cfg: Any) -> dict[str, Any]:
    from binge_schedule.content_catalog import canonical_rows_from_config

    episode_keys: set[str] = set()
    shows: dict[str, dict[str, Any]] = {}
    movies: dict[str, int] = {}

    for row in canonical_rows_from_config(cfg):
        import_shape = _catalog_row_as_import(row)
        episode_keys.add(import_row_identity_key(import_shape))
        raw_type = _normalize_key(import_shape.get("content_type", ""))
        show_key = _normalize_key(import_shape.get("display_name", ""))
        if not show_key:
            continue
        if raw_type == "series":
            bucket = shows.setdefault(
                show_key,
                {
                    "display_name": _clean_text(row.get("display_name", "")) or show_key,
                    "episode_count": 0,
                    "content_type": "series",
                },
            )
            bucket["episode_count"] += 1
        else:
            movies[show_key] = movies.get(show_key, 0) + 1

    return {"episode_keys": episode_keys, "shows": shows, "movies": movies}


_CATALOG_MATCH_LABELS = {
    "update": "Update",
    "new_episode": "New episode",
    "new_show": "New show",
    "new_movie": "New movie",
}


def _apply_catalog_matching(all_rows: list[dict[str, Any]], cfg: Any | None) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    if cfg is None:
        return all_rows, {}, []

    index = build_catalog_index(cfg)
    match_stats = {
        "new_shows": 0,
        "new_episodes": 0,
        "updates": 0,
        "new_movies": 0,
    }
    show_buckets: dict[str, dict[str, Any]] = {}
    incoming_shows: set[str] = set()

    for row in all_rows:
        key = import_row_identity_key(row)
        show_key = _normalize_key(row.get("display_name", "") or row.get("series_title", ""))
        raw_type = _normalize_key(row.get("content_type", ""))
        is_series = raw_type == "series" or (
            raw_type not in {"movie", "movies", "paid_programming", "literal"}
            and bool(_clean_text(row.get("episode_number", "")) or _clean_text(row.get("episode_title", "")))
        )

        if key in index["episode_keys"]:
            match = "update"
        elif is_series:
            if show_key in index["shows"] or show_key in incoming_shows:
                match = "new_episode"
            else:
                match = "new_show"
            if show_key:
                incoming_shows.add(show_key)
        elif show_key in index["movies"] or key in index["episode_keys"]:
            match = "update"
        else:
            match = "new_movie"

        row["catalog_match"] = match
        row["catalog_match_label"] = _CATALOG_MATCH_LABELS.get(match, match)
        if match == "new_show":
            match_stats["new_shows"] += 1
        elif match == "new_episode":
            match_stats["new_episodes"] += 1
        elif match == "update":
            match_stats["updates"] += 1
        elif match == "new_movie":
            match_stats["new_movies"] += 1

        show_key = _normalize_key(row.get("display_name", "") or row.get("series_title", ""))
        if not show_key:
            continue
        bucket = show_buckets.setdefault(
            show_key,
            {
                "show_name": _clean_text(row.get("display_name", "")) or show_key,
                "in_catalog": show_key in index["shows"] or show_key in index["movies"],
                "catalog_episode_count": 0,
                "new_episodes": 0,
                "updates": 0,
                "is_new_show": False,
            },
        )
        if show_key in index["shows"]:
            bucket["catalog_episode_count"] = int(index["shows"][show_key].get("episode_count", 0))
        elif show_key in index["movies"]:
            bucket["catalog_episode_count"] = int(index["movies"].get(show_key, 0))
        if match == "new_show":
            bucket["is_new_show"] = True
        elif match == "new_episode":
            bucket["new_episodes"] += 1
        elif match == "update":
            bucket["updates"] += 1

    show_summaries = sorted(
        show_buckets.values(),
        key=lambda item: (-(item["new_episodes"] + item["updates"]), item["show_name"].lower()),
    )
    return all_rows, match_stats, show_summaries


def catalog_hint_for_sheet(cfg: Any | None, sheet_name: str, default_series_title: str = "") -> dict[str, Any] | None:
    if cfg is None:
        return None
    index = build_catalog_index(cfg)
    for candidate in (_normalize_key(default_series_title), _normalize_key(sheet_name)):
        if not candidate:
            continue
        if candidate in index["shows"]:
            info = index["shows"][candidate]
            return {
                "show_name": info["display_name"],
                "in_catalog": True,
                "catalog_episode_count": int(info["episode_count"]),
                "content_type": "series",
            }
        if candidate in index["movies"]:
            return {
                "show_name": default_series_title or sheet_name,
                "in_catalog": True,
                "catalog_episode_count": int(index["movies"][candidate]),
                "content_type": "movie",
            }
    return None


def preview_import(session_id: str, sheet_configs: list[dict[str, Any]], cfg: Any | None = None) -> dict[str, Any]:
    session = get_import_session(session_id)
    source_name = str(session["filename"])
    all_rows: list[dict[str, Any]] = []
    all_issues: list[dict[str, Any]] = []
    per_sheet: list[dict[str, Any]] = []

    for raw_config in sheet_configs:
        config = SheetImportConfig.from_dict(raw_config)
        if not config.include:
            continue
        df_raw = session["sheets"].get(config.sheet_name)
        if df_raw is None:
            all_issues.append(
                {
                    "sheet": config.sheet_name,
                    "row": None,
                    "level": "error",
                    "message": "Sheet not found in uploaded file.",
                }
            )
            continue
        norm = build_sheet_dataframe(df_raw, config)
        rows, issues = rows_from_sheet(
            norm,
            sheet_name=config.sheet_name,
            source_name=source_name,
            config=config,
        )
        all_rows.extend(rows)
        all_issues.extend(issues)
        per_sheet.append({"sheet_name": config.sheet_name, "row_count": len(rows), "issues": len(issues)})

    ready = len(all_rows)
    skipped = sum(1 for issue in all_issues if issue.get("level") == "skipped")
    warnings = sum(1 for issue in all_issues if issue.get("level") == "warning")
    errors = sum(1 for issue in all_issues if issue.get("level") == "error")

    all_rows, match_stats, show_summaries = _apply_catalog_matching(all_rows, cfg)

    preview_limit = 100
    preview_rows = all_rows[:preview_limit]
    for row in preview_rows:
        for key in ("runtime_minutes",):
            if row.get(key) is not None:
                try:
                    row[key] = int(row[key])
                except (TypeError, ValueError):
                    pass

    return {
        "ready_count": ready,
        "warning_count": warnings,
        "skipped_count": skipped,
        "error_count": errors,
        "total_count": ready,
        "preview_rows": preview_rows,
        "issues": all_issues[:200],
        "per_sheet": per_sheet,
        "can_import": ready > 0 and errors == 0 and bool(mapping_has_title(sheet_configs)),
        "match_stats": match_stats,
        "show_summaries": show_summaries[:40],
    }


def mapping_has_title(sheet_configs: list[dict[str, Any]]) -> bool:
    for raw in sheet_configs:
        if not raw.get("include", True):
            continue
        mapping = raw.get("mapping") if isinstance(raw.get("mapping"), dict) else {}
        if mapping.get("title"):
            return True
    return False


def commit_import(cfg: Any, session_id: str, sheet_configs: list[dict[str, Any]]) -> dict[str, Any]:
    preview = preview_import(session_id, sheet_configs)
    if preview["error_count"] > 0:
        raise ValueError("Fix mapping errors before importing.")
    if preview["ready_count"] <= 0:
        raise ValueError("No rows to import.")
    if not preview["can_import"]:
        raise ValueError("Map episode or movie title for at least one included sheet.")

    session = get_import_session(session_id)
    source_name = str(session["filename"])
    all_rows: list[dict[str, Any]] = []

    for raw_config in sheet_configs:
        config = SheetImportConfig.from_dict(raw_config)
        if not config.include:
            continue
        df_raw = session["sheets"].get(config.sheet_name)
        if df_raw is None:
            continue
        norm = build_sheet_dataframe(df_raw, config)
        rows, _ = rows_from_sheet(
            norm,
            sheet_name=config.sheet_name,
            source_name=source_name,
            config=config,
        )
        all_rows.extend(rows)

    if not all_rows:
        raise ValueError("No content rows to import.")

    result = import_content_rows(cfg, all_rows)
    _IMPORT_SESSIONS.pop(session_id, None)
    result["imported_row_count"] = preview["ready_count"]
    result["warning_count"] = preview["warning_count"]
    result["skipped_count"] = preview["skipped_count"]
    result["match_stats"] = preview.get("match_stats", {})
    return result
