from __future__ import annotations

from datetime import datetime
from datetime import date, timedelta
from io import BytesIO
import json
from pathlib import Path
import os
import sys
import threading
from typing import Any, Optional
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, Side
from pydantic import BaseModel, Field
import yaml

from binge_schedule.config_io import load_build_config
from binge_schedule.content_catalog import canonical_rows_from_config
from binge_schedule.rule_analyzer import analyze_schedule_rules
from binge_schedule.schedule_blocks import blocks_to_week_grid, empty_slots_for_blocks, grid_to_blocks


DEFAULT_CONFIG = Path("config/april_2026.yaml")


class BlocksPayload(BaseModel):
    blocks: list[dict[str, Any]] = Field(default_factory=list)
    catalog_rows: list[dict[str, Any]] = Field(default_factory=list)


class BlocksToGridPayload(BaseModel):
    week_monday: date
    blocks: list[dict[str, Any]] = Field(default_factory=list)
    require_complete: bool = False


class GridToBlocksPayload(BaseModel):
    week_monday: date
    grid: list[list[Optional[str]]]


class SaveBaseSchedulePayload(BaseModel):
    station_id: str
    week_monday: date
    week_count: int = 1
    blocks: list[dict[str, Any]] = Field(default_factory=list)
    suggested_rules: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[dict[str, Any]] = Field(default_factory=list)


class DownloadSchedulePayload(BaseModel):
    station_id: str = ""
    week_monday: date
    week_count: int = 1
    blocks: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[dict[str, Any]] = Field(default_factory=list)


class AutoGeneratePayload(BaseModel):
    base_path: str = ""
    week_count: int = 1


def create_app() -> FastAPI:
    app = FastAPI(title="Playlist Schedule Builder API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "features": {
                "auto_generate_weeks": True,
                "auto_generate_date_shift": True,
            },
        }

    @app.post("/api/desktop/shutdown")
    def desktop_shutdown() -> dict[str, bool]:
        """Close the packaged desktop process when the UI browser tab exits."""
        is_desktop = os.environ.get("SCHEDULE_BUILDER_DESKTOP_RUNTIME") == "1"
        if is_desktop:
            threading.Timer(0.25, lambda: os._exit(0)).start()
        return {"desktop_runtime": is_desktop, "shutdown_requested": is_desktop}

    @app.get("/api/content-catalog")
    def content_catalog(config: str = str(DEFAULT_CONFIG)) -> dict[str, Any]:
        if Path(config) == DEFAULT_CONFIG:
            static_payload = _static_catalog_payload()
            if static_payload is not None:
                return static_payload
        cfg_path = _safe_config_path(config)
        cfg = load_build_config(cfg_path)
        rows = canonical_rows_from_config(cfg)
        return {
            "schema_version": 1,
            "row_count": len(rows),
            "rows": rows,
        }

    @app.get("/api/base-schedules")
    def base_schedules() -> dict[str, Any]:
        schedules = _builder_base_schedules()
        ready = sorted(
            [item for item in schedules if item["ready_to_generate"]],
            key=_base_schedule_sort_key,
            reverse=True,
        )
        return {
            "count": len(schedules),
            "ready_count": len(ready),
            "schedules": schedules,
            "active": ready[0] if ready else None,
        }

    @app.post("/api/schedule/analyze-rules")
    def analyze_rules(payload: BlocksPayload) -> dict[str, Any]:
        rules = analyze_schedule_rules(payload.blocks, catalog_rows=payload.catalog_rows)
        return {
            "rule_count": len(rules),
            "rules": [rule.to_dict() for rule in rules],
        }

    @app.post("/api/schedule/blocks-to-grid")
    def blocks_to_grid(payload: BlocksToGridPayload) -> dict[str, Any]:
        try:
            grid = blocks_to_week_grid(
                payload.blocks,
                week_monday=payload.week_monday,
                require_complete=payload.require_complete,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        missing = empty_slots_for_blocks(payload.blocks, week_monday=payload.week_monday)
        return {
            "week_monday": payload.week_monday.isoformat(),
            "missing_slot_count": len(missing),
            "missing_slots": [{"slot": slot, "day_index": day_index} for slot, day_index in missing[:200]],
            "grid": grid,
        }

    @app.post("/api/schedule/grid-to-blocks")
    def grid_to_calendar_blocks(payload: GridToBlocksPayload) -> dict[str, Any]:
        try:
            blocks = grid_to_blocks(payload.grid, week_monday=payload.week_monday)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "week_monday": payload.week_monday.isoformat(),
            "block_count": len(blocks),
            "blocks": [block.to_dict() for block in blocks],
        }

    @app.post("/api/schedule/download/{report_kind}")
    def download_schedule_report(report_kind: str, payload: DownloadSchedulePayload) -> StreamingResponse:
        week_count = _bounded_week_count(payload.week_count)
        station_label = _station_label(payload.station_id)
        if report_kind == "binge":
            data = _build_binge_preview_workbook(payload.blocks, station_id=payload.station_id)
            filename = f"{station_label}.xlsx"
        elif report_kind == "grids":
            data = _build_grids_preview_workbook(
                payload.blocks,
                station_id=payload.station_id,
                week_monday=payload.week_monday,
                week_count=week_count,
            )
            filename = f"{station_label} GRIDS.xlsx"
        else:
            raise HTTPException(status_code=404, detail="Unknown report kind")
        return StreamingResponse(
            BytesIO(data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.post("/api/schedule/download-package")
    def download_schedule_package(payload: DownloadSchedulePayload) -> StreamingResponse:
        week_count = _bounded_week_count(payload.week_count)
        station_label = _station_label(payload.station_id)
        data = _build_download_package(
            payload.blocks,
            notes=payload.notes,
            station_id=payload.station_id,
            week_monday=payload.week_monday,
            week_count=week_count,
        )
        return StreamingResponse(
            BytesIO(data),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{station_label} Reports.zip"'},
        )

    @app.post("/api/schedule/auto-generate")
    def auto_generate_schedule(payload: AutoGeneratePayload) -> dict[str, Any]:
        base = _load_builder_base_schedule(payload.base_path)
        marker = base["marker"]
        generate_week_count = _bounded_week_count(payload.week_count)
        blocks, week_monday, week_count = _auto_generate_blocks(
            base["path"],
            base["raw"],
            generate_week_count=generate_week_count,
        )
        return {
            "station_id": str(marker.get("station_id") or ""),
            "week_monday": week_monday.isoformat(),
            "week_count": week_count,
            "blocks": blocks,
        }

    @app.post("/api/base-schedules/save")
    def save_base_schedule(payload: SaveBaseSchedulePayload) -> dict[str, Any]:
        station_id = payload.station_id.strip()
        if not station_id:
            raise HTTPException(status_code=400, detail="Station ID is required")
        if not payload.blocks:
            raise HTTPException(status_code=400, detail="Schedule has no blocks")
        week_count = _bounded_week_count(payload.week_count)
        missing = []
        for week_index in range(week_count):
            week_monday = payload.week_monday + timedelta(days=week_index * 7)
            missing.extend(empty_slots_for_blocks(payload.blocks, week_monday=week_monday))
        if missing:
            raise HTTPException(status_code=400, detail=f"Schedule has {len(missing)} empty half-hour slots")
        path = _save_builder_base_schedule(
            station_id=station_id,
            week_monday=payload.week_monday,
            week_count=week_count,
            blocks=payload.blocks,
            suggested_rules=payload.suggested_rules,
            notes=payload.notes,
        )
        return {
            "saved": True,
            "path": path.as_posix(),
            "label": _base_schedule_label(path, station_id),
            "station_id": station_id,
        }

    ui_dist = _ui_dist_path()
    if ui_dist is not None:
        app.mount("/", StaticFiles(directory=ui_dist, html=True), name="scheduler-ui")

    return app


def _static_catalog_payload() -> dict[str, Any] | None:
    path = _static_catalog_path()
    if path is None:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        return payload
    return None


def _static_catalog_path() -> Path | None:
    candidates: list[Path] = []
    ui_dist = _ui_dist_path()
    if ui_dist is not None:
        candidates.append(ui_dist / "content-catalog.json")

    module_root = Path(__file__).resolve().parents[1]
    exe_dir = Path(sys.executable).resolve().parent
    meipass = Path(getattr(sys, "_MEIPASS", "")) if getattr(sys, "_MEIPASS", None) else None
    candidates.extend(
        [
            Path.cwd() / "scheduler-ui" / "public" / "content-catalog.json",
            Path.cwd() / "scheduler-ui" / "dist" / "content-catalog.json",
            module_root / "scheduler-ui" / "public" / "content-catalog.json",
            module_root / "scheduler-ui" / "dist" / "content-catalog.json",
            exe_dir / "scheduler-ui" / "dist" / "content-catalog.json",
            exe_dir / "_internal" / "scheduler-ui" / "dist" / "content-catalog.json",
        ]
    )
    if meipass is not None:
        candidates.append(meipass / "scheduler-ui" / "dist" / "content-catalog.json")

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _ui_dist_path() -> Path | None:
    env_path = os.environ.get("SCHEDULE_BUILDER_REACT_DIST", "").strip()
    candidates: list[Path] = []
    if env_path:
        candidates.append(Path(env_path))

    module_root = Path(__file__).resolve().parents[1]
    exe_dir = Path(sys.executable).resolve().parent
    meipass = Path(getattr(sys, "_MEIPASS", "")) if getattr(sys, "_MEIPASS", None) else None
    candidates.extend(
        [
            Path.cwd() / "scheduler-ui" / "dist",
            module_root / "scheduler-ui" / "dist",
            exe_dir / "scheduler-ui" / "dist",
            exe_dir / "_internal" / "scheduler-ui" / "dist",
        ]
    )
    if meipass is not None:
        candidates.append(meipass / "scheduler-ui" / "dist")

    for candidate in candidates:
        if (candidate / "index.html").is_file():
            return candidate
    return None


def _safe_config_path(raw: str) -> Path:
    path = Path(raw or str(DEFAULT_CONFIG))
    if path.is_absolute():
        p = path
    else:
        p = (Path.cwd() / path).resolve()
    if not p.is_file():
        raise HTTPException(status_code=404, detail=f"Config not found: {raw}")
    if p.suffix.lower() not in {".yaml", ".yml"}:
        raise HTTPException(status_code=400, detail="Config path must be a YAML file")
    return p


def _save_builder_base_schedule(
    *,
    station_id: str,
    week_monday: date,
    week_count: int,
    blocks: list[dict[str, Any]],
    suggested_rules: list[dict[str, Any]],
    notes: list[dict[str, Any]],
) -> Path:
    safe_station = _safe_station_id(station_id)
    created_at = datetime.now()
    save_dir = _saved_schedule_dir(safe_station, created_at)
    path = save_dir / "base_schedule.yaml"
    save_dir.mkdir(parents=True, exist_ok=True)
    source = _base_schedule_source_config()
    base = {
        "gracenote_binge_id": int(source.get("gracenote_binge_id", 0) or 0),
        "nikki_workbook": source.get("nikki_workbook") or "../data/2024 Nikki Spreadsheets.xlsx",
        "timezone_note": source.get("timezone_note") or "local",
        "wrap_episodes": bool(source.get("wrap_episodes", True)),
        "cursor_state_file": f"episode_cursors_{safe_station}.json",
        "schedule_builder": {
            "managed": True,
            "kind": "base_schedule",
            "source": "react_schedule_builder",
            "station_id": station_id,
            "week_monday": week_monday.isoformat(),
            "week_count": week_count,
            "created_at": created_at.isoformat(timespec="seconds"),
            "saved_directory": save_dir.as_posix(),
            "draft_block_count": len(blocks),
            "draft_blocks": blocks,
            "suggested_rules": suggested_rules,
            "notes": notes,
        },
        "shows": source.get("shows") if isinstance(source.get("shows"), dict) else {},
        "weeks": [
            {
                "monday": (week_monday + timedelta(days=week_index * 7)).isoformat(),
                "grids_file": f"../data/base_schedules/{safe_station}/base_schedule_grids.xlsx",
                "sheet_name": _sheet_name_for_week(week_monday + timedelta(days=week_index * 7)),
            }
            for week_index in range(week_count)
        ],
    }
    path.write_text(yaml.safe_dump(base, sort_keys=False, allow_unicode=False), encoding="utf-8")
    station_label = _station_label(station_id)
    (save_dir / f"{station_label}.xlsx").write_bytes(_build_binge_preview_workbook(blocks, station_id=station_id))
    (save_dir / f"{station_label} GRIDS.xlsx").write_bytes(
        _build_grids_preview_workbook(blocks, station_id=station_id, week_monday=week_monday, week_count=week_count)
    )
    (save_dir / "Warnings and Notes.csv").write_text(_notes_csv(notes, station_id=station_id), encoding="utf-8")
    _save_auto_cursors(save_dir / f"episode_cursors_{safe_station}.json", _seed_cursors_from_template(blocks, _catalog_episodes_by_show()))
    return path


def _build_binge_preview_workbook(blocks: list[dict[str, Any]], *, station_id: str = "") -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = _station_label(station_id)[:31]
    headers = ["Station ID", "Date", "Start", "End", "Show", "Episode", "Slot", "Runtime", "Avails"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="left")
    for block in sorted(blocks, key=lambda item: str(item.get("start") or "")):
        start = _parse_iso_datetime(block.get("start"))
        end = _parse_iso_datetime(block.get("end"))
        slot_minutes = _minutes_between(start, end)
        runtime = _float_or_none(block.get("runtimeMinutes") or block.get("runtime_minutes"))
        episode = _episode_label(block)
        ws.append(
            [
                station_id,
                start.date().isoformat() if start else "",
                _clock_label(start),
                _clock_label(end),
                str(block.get("show") or ""),
                episode,
                f"{slot_minutes} min" if slot_minutes is not None else "",
                _duration_label(runtime),
                _duration_label(max(0, slot_minutes - runtime)) if slot_minutes is not None and runtime is not None else "",
            ]
        )
    _autosize_columns(ws)
    return _workbook_bytes(wb)


def _build_grids_preview_workbook(
    blocks: list[dict[str, Any]],
    *,
    station_id: str = "",
    week_monday: date,
    week_count: int,
) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    station_label = _station_label(station_id)
    for week_index in range(week_count):
        monday = week_monday + timedelta(days=week_index * 7)
        grid = blocks_to_week_grid(blocks, week_monday=monday, require_complete=False)
        ws = wb.create_sheet(_sheet_name_for_week(monday))
        ws.append(["", "", "", "", station_label, "", "", "", ""])
        ws.append(["", "", "", "", f"Week of {monday.isoformat()}", "", "", "", ""])
        ws.append(["", *[(monday + timedelta(days=i)).isoformat() for i in range(7)], ""])
        ws.append([station_label, "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", station_label])
        for slot in range(48):
            time_label = _slot_label(slot)
            ws.append([time_label, *[_grid_show_only(grid[slot][day]) for day in range(7)], time_label])
        _merge_grids_blocks(ws, blocks, monday)
        _apply_grid_borders(ws)
        for row in ws.iter_rows():
            for cell in row:
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for cell in ws[1] + ws[2] + ws[3] + ws[4]:
            cell.font = Font(bold=True)
        _autosize_columns(ws, max_width=26)
    return _workbook_bytes(wb)


def _build_download_package(
    blocks: list[dict[str, Any]],
    *,
    notes: list[dict[str, Any]],
    station_id: str = "",
    week_monday: date,
    week_count: int,
) -> bytes:
    out = BytesIO()
    station_label = _station_label(station_id)
    with ZipFile(out, "w", ZIP_DEFLATED) as archive:
        archive.writestr(f"{station_label}.xlsx", _build_binge_preview_workbook(blocks, station_id=station_id))
        archive.writestr(
            f"{station_label} GRIDS.xlsx",
            _build_grids_preview_workbook(blocks, station_id=station_id, week_monday=week_monday, week_count=week_count),
        )
        archive.writestr("Warnings and Notes.csv", _notes_csv(notes, station_id=station_id))
    return out.getvalue()


def _notes_csv(notes: list[dict[str, Any]], *, station_id: str = "") -> str:
    rows = [["Station ID", "Type", "Show", "Message"]]
    for note in notes:
        rows.append(
            [
                station_id,
                str(note.get("kind") or ""),
                str(note.get("show") or ""),
                str(note.get("message") or ""),
            ]
        )
    return "\n".join(",".join(_csv_escape(cell) for cell in row) for row in rows) + "\n"


def _csv_escape(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def _merge_grids_blocks(ws, blocks: list[dict[str, Any]], week_monday: date) -> None:
    """Match the GRIDS report look: long programs are one merged vertical cell."""
    for block in blocks:
        start = _parse_iso_datetime(block.get("start"))
        end = _parse_iso_datetime(block.get("end"))
        if start is None or end is None:
            continue
        day_index = (start.date() - week_monday).days
        if day_index < 0 or day_index > 6:
            continue
        start_slot = _datetime_to_slot_start(start)
        end_slot = _datetime_to_end_slot(start, end)
        if end_slot <= start_slot:
            continue
        row = 5 + start_slot
        col = 2 + day_index
        ws.cell(row=row, column=col).value = str(block.get("show") or ws.cell(row=row, column=col).value or "")
        if end_slot - start_slot > 1:
            ws.merge_cells(start_row=row, start_column=col, end_row=5 + end_slot - 1, end_column=col)


def _apply_grid_borders(ws) -> None:
    thin = Side(style="thin", color="000000")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for row in ws.iter_rows(min_row=4, max_row=52, min_col=1, max_col=9):
        for cell in row:
            cell.border = border


def _parse_iso_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _minutes_between(start: datetime | None, end: datetime | None) -> int | None:
    if start is None or end is None:
        return None
    return max(0, int(round((end - start).total_seconds() / 60)))


def _datetime_to_slot_start(value: datetime) -> int:
    minutes = value.hour * 60 + value.minute
    return max(0, min(47, minutes // 30))


def _datetime_to_end_slot(start: datetime, end: datetime) -> int:
    if end.date() > start.date():
        return 48
    minutes = end.hour * 60 + end.minute
    return max(0, min(48, (minutes + 29) // 30))


def _clock_label(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.strftime("%I:%M %p").lstrip("0")


def _slot_label(slot: int) -> str:
    total = slot * 30
    hour = total // 60
    minute = total % 60
    return datetime(2026, 1, 1, hour, minute).strftime("%I:%M %p").lstrip("0")


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _duration_label(minutes: float | None) -> str:
    if minutes is None:
        return ""
    total_seconds = int(round(minutes * 60))
    mins = total_seconds // 60
    seconds = total_seconds % 60
    return f"{mins}:{seconds:02d}" if seconds else f"{mins} min"


def _episode_label(block: dict[str, Any]) -> str:
    code = str(block.get("episodeCode") or block.get("episode_code") or "").strip()
    title = str(block.get("episodeTitle") or block.get("episode_title") or "").strip()
    return " - ".join(part for part in (code, title) if part)


def _grid_show_only(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    first = text.splitlines()[0].strip()
    if " - (" in first:
        first = first.split(" - (", 1)[0].strip()
    return first


def _autosize_columns(ws, *, max_width: int = 42) -> None:
    for column_cells in ws.columns:
        letter = column_cells[0].column_letter
        longest = max(len(str(cell.value or "")) for cell in column_cells)
        ws.column_dimensions[letter].width = min(max_width, max(10, longest + 2))


def _workbook_bytes(wb: Workbook) -> bytes:
    out = BytesIO()
    wb.save(out)
    return out.getvalue()


def _bounded_week_count(raw: int) -> int:
    try:
        val = int(raw)
    except Exception:
        return 1
    return max(1, min(4, val))


def _sheet_name_for_week(week_monday: date) -> str:
    return f"{week_monday.month}-{week_monday.day}-{week_monday.year}"


def _base_schedule_source_config() -> dict[str, Any]:
    for path in (Path("config") / "blank_schedule.yaml", DEFAULT_CONFIG):
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(raw, dict):
            return raw
    return {}


def _load_builder_base_schedule(raw_path: str = "") -> dict[str, Any]:
    schedules = _builder_base_schedules()
    selected: Path | None = None
    if raw_path.strip():
        requested = Path(raw_path.strip())
        for item in schedules:
            path = Path(str(item.get("path") or ""))
            if path == requested or path.as_posix() == requested.as_posix():
                selected = path
                break
        if selected is None and requested.is_file() and requested.name == "base_schedule.yaml":
            selected = requested
    elif schedules:
        ready = [item for item in schedules if item.get("ready_to_generate")]
        if ready:
            selected = Path(str(ready[0]["path"]))
    if selected is None or not selected.is_file():
        raise HTTPException(status_code=404, detail="No saved base schedule found")
    try:
        raw = yaml.safe_load(selected.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read base schedule: {selected}") from exc
    if not isinstance(raw, dict):
        raise HTTPException(status_code=400, detail="Saved base schedule is not valid")
    marker = raw.get("schedule_builder")
    if not isinstance(marker, dict) or marker.get("managed") is not True:
        raise HTTPException(status_code=400, detail="Saved schedule is not builder-managed")
    return {"path": selected, "raw": raw, "marker": marker}


def _parse_week_monday(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Saved base schedule has an invalid week_monday") from exc


def _remint_block_id(block: dict[str, Any], start: datetime) -> str:
    raw_id = str(block.get("id") or "block")
    stem = raw_id.rsplit("-", 1)[0] if "-" in raw_id else raw_id
    return f"{stem}-{int(start.timestamp() * 1000)}"


def _auto_generate_blocks(
    base_path: Path,
    raw: dict[str, Any],
    *,
    generate_week_count: int,
) -> tuple[list[dict[str, Any]], date, int]:
    marker = raw.get("schedule_builder") if isinstance(raw.get("schedule_builder"), dict) else {}
    template_blocks = marker.get("draft_blocks") if isinstance(marker.get("draft_blocks"), list) else []
    if not template_blocks:
        raise HTTPException(status_code=400, detail="Saved base schedule has no template blocks")
    template_week_count = _bounded_week_count(int(marker.get("week_count") or 1))
    generate_week_count = _bounded_week_count(generate_week_count)
    base_monday = _parse_week_monday(marker.get("week_monday"))
    next_monday = base_monday + timedelta(days=template_week_count * 7)

    station_id = str(marker.get("station_id") or "")
    safe_station = _safe_station_id(station_id)
    cursor_path = base_path.parent / f"episode_cursors_{safe_station}.json"
    episodes_by_show = _catalog_episodes_by_show()
    cursors = _load_auto_cursors(cursor_path)
    if not cursors:
        cursors = _seed_cursors_from_template(template_blocks, episodes_by_show)

    generated: list[dict[str, Any]] = []
    for gen_week_index in range(generate_week_count):
        template_week_index = gen_week_index % template_week_count
        target_week_monday = next_monday + timedelta(days=gen_week_index * 7)
        template_week_start = base_monday + timedelta(days=template_week_index * 7)

        for block in sorted(template_blocks, key=lambda item: str(item.get("start") or "")):
            start = _parse_iso_datetime(block.get("start"))
            end = _parse_iso_datetime(block.get("end"))
            if start is None:
                continue
            block_template_week = (start.date() - base_monday).days // 7
            if block_template_week != template_week_index:
                continue

            day_offset = start.date() - template_week_start
            new_start = datetime.combine(target_week_monday + day_offset, start.time())
            if end is not None:
                new_end = new_start + (end - start)
            else:
                new_end = new_start + timedelta(minutes=30)

            next_block = dict(block)
            next_block["start"] = new_start.isoformat(timespec="seconds")
            next_block["end"] = new_end.isoformat(timespec="seconds")
            next_block["id"] = _remint_block_id(block, new_start)

            show = str(next_block.get("show") or "").strip()
            if _auto_generates_episode(next_block) and show in episodes_by_show:
                episodes = episodes_by_show[show]
                if episodes:
                    index = int(cursors.get(show, 0) or 0) % len(episodes)
                    episode = episodes[index]
                    cursors[show] = (index + 1) % len(episodes)
                    next_block.update(
                        {
                            "episodeId": episode["id"],
                            "episode_id": episode["id"],
                            "episodeCode": episode["code"],
                            "episodeTitle": episode["title"],
                            "title": " ".join(part for part in (episode["code"], episode["title"]) if part).strip(),
                            "runtimeMinutes": episode["runtime_minutes"],
                            "content_type": episode["content_type"],
                            "contentType": episode["content_type"],
                        }
                    )
            generated.append(next_block)

    generated.sort(key=lambda item: str(item.get("start") or ""))
    return generated, next_monday, generate_week_count


def _catalog_episodes_by_show() -> dict[str, list[dict[str, Any]]]:
    payload = _static_catalog_payload()
    rows: list[dict[str, Any]]
    if payload is not None and isinstance(payload.get("rows"), list):
        rows = payload["rows"]
    else:
        cfg = load_build_config(DEFAULT_CONFIG)
        rows = canonical_rows_from_config(cfg)
    by_show: dict[str, list[dict[str, Any]]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        if row.get("availability_status") and row.get("availability_status") not in {"available", "metadata_only"}:
            continue
        content_type = _frontend_content_type(str(row.get("content_type") or ""))
        if content_type != "Series / show":
            continue
        show = str(row.get("display_name") or "").strip()
        if not show:
            continue
        scheduled = _float_or_none(row.get("binge_row_minutes") or row.get("runtime_minutes")) or 30
        runtime = _float_or_none(row.get("runtime_minutes")) or scheduled
        episode = {
            "id": str(row.get("episode_key") or f"{row.get('series_key') or show}-{index}"),
            "show": show,
            "code": str(row.get("episode_code") or row.get("episode_number") or "EP").strip(),
            "title": str(row.get("episode_title") or show).strip(),
            "runtime_minutes": runtime,
            "content_type": content_type,
        }
        by_show.setdefault(show, []).append(episode)
    return by_show


def _frontend_content_type(value: str) -> str:
    normalized = value.lower().replace(" ", "_")
    if normalized in {"movie", "movies", "special", "specials", "film", "feature"}:
        return "Movie / special"
    if normalized in {"paid", "paid_programming", "infomercial", "ministry"}:
        return "Paid programming"
    return "Series / show"


def _auto_generates_episode(block: dict[str, Any]) -> bool:
    content_type = str(block.get("contentType") or block.get("content_type") or "").casefold()
    code = str(block.get("episodeCode") or block.get("episode_code") or "").upper()
    if "paid" in content_type or code in {"PAID", "LIT"}:
        return False
    if "movie" in content_type:
        return False
    return True


def _load_auto_cursors(path: Path) -> dict[str, int]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    raw = payload.get("cursors") if isinstance(payload, dict) else {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, int] = {}
    for show, value in raw.items():
        try:
            out[str(show)] = max(0, int(value))
        except (TypeError, ValueError):
            continue
    return out


def _save_auto_cursors(path: Path, cursors: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"cursors": cursors}, indent=2), encoding="utf-8")


def _seed_cursors_from_template(
    blocks: list[dict[str, Any]],
    episodes_by_show: dict[str, list[dict[str, Any]]],
) -> dict[str, int]:
    cursors: dict[str, int] = {}
    for block in blocks:
        if not _auto_generates_episode(block):
            continue
        show = str(block.get("show") or "").strip()
        episodes = episodes_by_show.get(show) or []
        if not episodes:
            continue
        pos = _episode_position(block, episodes)
        if pos is not None:
            cursors[show] = max(cursors.get(show, 0), pos + 1)
    for show, episodes in episodes_by_show.items():
        if show in cursors and episodes:
            cursors[show] = cursors[show] % len(episodes)
    return cursors


def _episode_position(block: dict[str, Any], episodes: list[dict[str, Any]]) -> int | None:
    tokens = {
        str(block.get("episodeId") or block.get("episode_id") or "").strip().casefold(),
        str(block.get("episodeCode") or block.get("episode_code") or "").strip().casefold(),
        str(block.get("episodeTitle") or block.get("episode_title") or "").strip().casefold(),
    }
    tokens.discard("")
    for index, episode in enumerate(episodes):
        if {
            str(episode.get("id") or "").strip().casefold(),
            str(episode.get("code") or "").strip().casefold(),
            str(episode.get("title") or "").strip().casefold(),
        } & tokens:
            return index
    return None


def _saved_schedules_root() -> Path:
    if os.environ.get("SCHEDULE_BUILDER_DESKTOP_RUNTIME") == "1" or getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "saved_schedules"
    return Path.cwd() / "saved_schedules"


def _saved_schedule_dir(safe_station: str, created_at: datetime) -> Path:
    return _saved_schedules_root() / safe_station / created_at.strftime("%Y-%m-%d_%H-%M-%S")


def _safe_station_id(station_id: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in station_id.strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned or "station"


def _station_label(station_id: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {" ", "-", "_"} else "_" for ch in station_id.strip()).strip() or "Station"


def _base_schedule_sort_key(item: dict[str, Any]) -> str:
    created = str(item.get("created_at") or "").strip()
    if created:
        return created
    return str(item.get("path") or "")


def _base_schedule_label(path: Path, station_id: str | None = None) -> str:
    sid = (station_id or "").strip()
    if sid:
        return f"Station {sid}"
    return path.stem.replace("_", " ").title()


def _builder_base_schedules() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    candidates: list[Path] = []
    config_dir = Path("config")
    if config_dir.is_dir():
        candidates.extend(sorted(config_dir.glob("*.yaml")))
    saved_root = _saved_schedules_root()
    if saved_root.is_dir():
        candidates.extend(sorted(saved_root.glob("*/base_schedule.yaml")))
        candidates.extend(sorted(saved_root.glob("*/*/base_schedule.yaml")))
    for path in candidates:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(raw, dict):
            continue
        marker = raw.get("schedule_builder")
        if not isinstance(marker, dict) or marker.get("managed") is not True:
            continue
        station_id = str(marker.get("station_id") or "").strip()
        weeks = raw.get("weeks") if isinstance(raw.get("weeks"), list) else []
        shows = raw.get("shows") if isinstance(raw.get("shows"), dict) else {}
        out.append(
            {
                "path": path.as_posix(),
                "label": _base_schedule_label(path, station_id),
                "station_id": station_id,
                "kind": marker.get("kind") or "base_schedule",
                "source": marker.get("source") or "",
                "week_count": int(marker.get("week_count") or len(weeks) or 1),
                "template_week_count": int(marker.get("week_count") or len(weeks) or 1),
                "week_monday": str(marker.get("week_monday") or ""),
                "created_at": str(marker.get("created_at") or ""),
                "show_count": len(shows),
                "draft_block_count": int(marker.get("draft_block_count") or 0),
                "ready_to_generate": int(marker.get("draft_block_count") or 0) > 0,
            }
        )
    return out


app = create_app()
