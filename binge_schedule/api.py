from __future__ import annotations

from datetime import date
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
        weeks = raw.get("weeks") if isinstance(raw.get("weeks"), list) else []
        shows = raw.get("shows") if isinstance(raw.get("shows"), dict) else {}
        out.append(
            {
                "path": path.as_posix(),
                "label": path.stem.replace("_", " ").title(),
                "kind": marker.get("kind") or "base_schedule",
                "source": marker.get("source") or "",
                "week_count": len(weeks),
                "show_count": len(shows),
                "ready_to_generate": bool(weeks),
            }
        )
    return out


app = create_app()
