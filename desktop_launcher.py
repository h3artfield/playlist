"""Windows desktop launcher for Schedule Builder.

Built with PyInstaller (one-folder mode). This entrypoint starts the bundled
Streamlit app and opens the local UI in the default browser.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from streamlit.web import cli as stcli


def _app_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


def main() -> int:
    root = _app_root()
    app_path = root / "streamlit_app.py"
    os.chdir(root)
    # Avoid telemetry prompts and keep desktop behavior predictable.
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.headless=false",
        "--browser.gatherUsageStats=false",
        "--server.fileWatcherType=none",
    ]
    return int(stcli.main())


if __name__ == "__main__":
    raise SystemExit(main())

