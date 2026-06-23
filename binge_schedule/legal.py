"""EULA text, version, and desktop installer download metadata."""

from __future__ import annotations

import os
from pathlib import Path

EULA_VERSION = "1.0.0"
EULA_FILENAME = "EULA.txt"


def eula_file_path() -> Path:
    return Path(__file__).resolve().parent.parent / "legal" / EULA_FILENAME


def read_eula_text() -> str:
    path = eula_file_path()
    if not path.is_file():
        return "End User License Agreement text is not available."
    return path.read_text(encoding="utf-8")


def _secret_or_env(key: str) -> str:
    return str(os.environ.get(key) or "").strip()


def desktop_download_meta() -> dict[str, str]:
    from binge_schedule.runtime_paths import desktop_app_version

    url = _secret_or_env("DESKTOP_APP_DOWNLOAD_URL")
    if not url:
        repo = _secret_or_env("DESKTOP_APP_GITHUB_REPO") or "h3artfield/playlist"
        url = f"https://github.com/{repo}/releases/latest/download/ScheduleBuilderSetup.exe"
    version = _secret_or_env("DESKTOP_APP_VERSION") or desktop_app_version()
    return {
        "url": url,
        "label": _secret_or_env("DESKTOP_APP_LABEL") or "Download Desktop App (Windows)",
        "version": version,
        "notes_url": _secret_or_env("DESKTOP_APP_RELEASE_NOTES_URL"),
        "eula_version": EULA_VERSION,
    }

