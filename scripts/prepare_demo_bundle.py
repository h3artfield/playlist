"""Copy the user's TEST saved schedule into packaging/demo_assets for desktop -Demo builds."""
from __future__ import annotations

import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "saved_schedules" / "test" / "2026-05-19_21-33-48"
DEMO_ASSETS = ROOT / "packaging" / "demo_assets"
DEST_DIR = DEMO_ASSETS / "saved_schedules" / "test" / "2026-05-19_21-33-48"
REL_SAVE_DIR = "saved_schedules/test/2026-05-19_21-33-48"


def _patch_base_schedule(path: Path) -> None:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid base schedule YAML: {path}")

    raw["nikki_workbook"] = "data/2024 Nikki Spreadsheets.xlsx"
    raw["cursor_state_file"] = "episode_cursors_test.json"

    marker = raw.get("schedule_builder")
    if isinstance(marker, dict):
        marker["saved_directory"] = REL_SAVE_DIR

    weeks = raw.get("weeks")
    if isinstance(weeks, list):
        for week in weeks:
            if isinstance(week, dict):
                week["grids_file"] = f"{REL_SAVE_DIR}/TEST GRIDS.xlsx"

    path.write_text(yaml.safe_dump(raw, sort_keys=False, allow_unicode=False), encoding="utf-8")


def main() -> None:
    if not SOURCE_DIR.is_dir():
        if DEST_DIR.is_dir() and (DEST_DIR / "base_schedule.yaml").is_file():
            print(f"Demo assets already present at {DEST_DIR} (skipping copy from saved_schedules/)")
            return
        raise SystemExit(
            f"Demo source not found: {SOURCE_DIR}\n"
            "Save station TEST in the app first, or copy your folder there."
        )

    if DEST_DIR.exists():
        shutil.rmtree(DEST_DIR)
    shutil.copytree(SOURCE_DIR, DEST_DIR)

    base = DEST_DIR / "base_schedule.yaml"
    if not base.is_file():
        raise SystemExit(f"Missing base_schedule.yaml in {SOURCE_DIR}")

    _patch_base_schedule(base)

    cursor_path = DEST_DIR / "episode_cursors_test.json"
    if not cursor_path.is_file():
        cursor_path.write_text("{}", encoding="utf-8")

    print(f"Demo schedule bundled at {DEST_DIR}")


if __name__ == "__main__":
    main()
