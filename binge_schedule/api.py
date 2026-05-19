from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path
import os
import sys
import threading
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
    def health() -> dict[str, str]:
        return {"status": "ok"}

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
        ready = [item for item in schedules if item["ready_to_generate"]]
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
) -> Path:
    safe_station = _safe_station_id(station_id)
    path = Path("config") / f"base_schedule_{safe_station}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
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
            "draft_block_count": len(blocks),
            "draft_blocks": blocks,
            "suggested_rules": suggested_rules,
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
    return path


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


def _safe_station_id(station_id: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in station_id.strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned or "station"


def _base_schedule_label(path: Path, station_id: str | None = None) -> str:
    sid = (station_id or "").strip()
    if sid:
        return f"Station {sid}"
    return path.stem.replace("_", " ").title()


def _builder_base_schedules() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    config_dir = Path("config")
    if not config_dir.is_dir():
        return out
    for path in sorted(config_dir.glob("*.yaml")):
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
                "week_count": len(weeks),
                "show_count": len(shows),
                "draft_block_count": int(marker.get("draft_block_count") or 0),
                "ready_to_generate": bool(weeks) and int(marker.get("draft_block_count") or 0) > 0,
            }
        )
    return out


app = create_app()
