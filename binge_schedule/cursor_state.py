"""Persist content-workbook episode cursors between runs (next episode per show)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from binge_schedule.models import BuildConfig, Catalog


def resolved_cursor_state_path(cfg: BuildConfig) -> Optional[Path]:
    if not cfg.cursor_state_file or not str(cfg.cursor_state_file).strip():
        return None
    raw = Path(cfg.cursor_state_file.strip())
    if raw.is_absolute():
        return raw
    base = cfg.config_path.parent if cfg.config_path else Path.cwd()
    return (base / raw).resolve()


def apply_saved_cursors(cat: Catalog, path: Optional[Path]) -> None:
    """If ``path`` exists, restore ``cat.cursor`` for each saved series key."""
    if path is None or not path.is_file():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    saved = data.get("cursors") or {}
    for key, idx in saved.items():
        if key not in cat.cursor or key not in cat.by_show:
            continue
        try:
            n = int(idx)
        except (TypeError, ValueError):
            continue
        eps = cat.by_show[key]
        if not eps:
            continue
        # Allow cursor == len(episodes) (finished list; next scheduling step may wrap).
        upper = len(eps)
        cat.cursor[key] = max(0, min(n, upper))


def save_cursors_after_export(cat: Catalog, path: Optional[Path]) -> None:
    """Write current episode indices for all series shows."""
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    cursors = {k: cat.cursor[k] for k in cat.by_show if k in cat.cursor}
    payload = {"cursors": cursors}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
