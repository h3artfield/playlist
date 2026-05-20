"""User preferences: theme, accent colors, primary/backup save directories."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from binge_schedule.runtime_paths import (
    is_desktop_runtime,
    local_app_data_dir,
    schedule_builder_data_dir,
)


def default_primary_save_directory() -> str:
    return (schedule_builder_data_dir() / "saved_schedules").resolve().as_posix()


def settings_file_path() -> Path:
    path = local_app_data_dir() / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def default_settings() -> dict[str, Any]:
    return {
        "theme": "dark",
        "accent_primary": "#2563eb",
        "accent_secondary": "#7c3aed",
        "primary_save_directory": default_primary_save_directory(),
        "backup_save_directory": "",
        "backup_enabled": True,
        "desktop_window_mode": "windowed",
    }


def normalize_desktop_window_mode(value: Any, *, fallback: str = "windowed") -> str:
    mode = str(value or fallback).strip().lower()
    if mode not in {"fullscreen", "windowed"}:
        return fallback if fallback in {"fullscreen", "windowed"} else "windowed"
    return mode


def load_settings() -> dict[str, Any]:
    path = settings_file_path()
    base = default_settings()
    if not path.is_file():
        return base
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return base
    if not isinstance(raw, dict):
        return base
    merged = {**base, **raw}
    if not str(merged.get("primary_save_directory") or "").strip():
        merged["primary_save_directory"] = base["primary_save_directory"]
    return merged


def save_settings(payload: dict[str, Any]) -> dict[str, Any]:
    current = load_settings()
    theme = str(payload.get("theme") or current["theme"]).strip().lower()
    if theme not in {"dark", "light"}:
        theme = "dark"
    primary = _normalize_directory(payload.get("primary_save_directory"), fallback=current["primary_save_directory"])
    backup_raw = str(payload.get("backup_save_directory") or "").strip()
    backup = _normalize_directory(backup_raw, fallback="") if backup_raw else ""
    if backup and _normalize_schedule_path_key(Path(primary)) == _normalize_schedule_path_key(Path(backup)):
        raise ValueError("Backup directory must be different from the primary save directory.")

    updated = {
        "theme": theme,
        "accent_primary": _normalize_hex_color(payload.get("accent_primary"), current["accent_primary"]),
        "accent_secondary": _normalize_hex_color(payload.get("accent_secondary"), current["accent_secondary"]),
        "primary_save_directory": primary,
        "backup_save_directory": backup,
        "backup_enabled": bool(payload.get("backup_enabled", current.get("backup_enabled", True))),
        "desktop_window_mode": normalize_desktop_window_mode(
            payload.get("desktop_window_mode"),
            fallback=str(current.get("desktop_window_mode") or "windowed"),
        ),
    }
    settings_file_path().write_text(json.dumps(updated, indent=2), encoding="utf-8")
    return updated


def primary_saved_schedules_root() -> Path:
    raw = str(load_settings().get("primary_save_directory") or "").strip()
    if raw:
        path = Path(raw)
        path.mkdir(parents=True, exist_ok=True)
        return path
    path = Path(default_primary_save_directory())
    path.mkdir(parents=True, exist_ok=True)
    return path


def backup_saved_schedules_root() -> Path | None:
    settings = load_settings()
    if not settings.get("backup_enabled"):
        return None
    raw = str(settings.get("backup_save_directory") or "").strip()
    if not raw:
        return None
    path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path


def mirror_saved_schedule_dir(save_dir: Path) -> Path | None:
    """Copy a freshly saved schedule folder to the backup root (same relative path)."""
    backup_root = backup_saved_schedules_root()
    if backup_root is None:
        return None
    primary_root = primary_saved_schedules_root()
    try:
        rel = save_dir.resolve().relative_to(primary_root.resolve())
    except ValueError:
        rel = Path(save_dir.name)
    dest = backup_root / rel
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(save_dir, dest)
    return dest


def pick_directory_dialog(*, title: str = "Choose folder") -> str:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError as exc:
        raise RuntimeError("Folder picker is not available in this environment.") from exc

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askdirectory(title=title, mustexist=False)
    finally:
        root.destroy()
    if not selected:
        return ""
    return Path(selected).resolve().as_posix()


def _normalize_directory(value: Any, *, fallback: str) -> str:
    text = str(value or "").strip()
    if not text:
        return str(fallback or "").strip()
    return Path(text).expanduser().resolve().as_posix()


def _normalize_hex_color(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    if not text.startswith("#"):
        text = f"#{text}"
    if len(text) == 7:
        try:
            int(text[1:], 16)
            return text.lower()
        except ValueError:
            pass
    return str(fallback).lower()


def _normalize_schedule_path_key(path: Path) -> str:
    try:
        return path.resolve().as_posix().casefold()
    except OSError:
        return path.as_posix().casefold()


def settings_for_api() -> dict[str, Any]:
    data = load_settings()
    data["desktop_runtime"] = is_desktop_runtime()
    data["settings_file"] = settings_file_path().as_posix()
    return data
