"""Windows desktop launcher for Schedule Builder.

Built with PyInstaller (one-folder mode). This entrypoint starts the bundled
Streamlit app and opens the local UI in the default browser.
"""

from __future__ import annotations

import contextlib
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

from streamlit.web import cli as stcli


def _logs_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home().as_posix()))
    p = base / "ScheduleBuilder" / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _show_error_dialog(title: str, message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        # If dialog cannot render, we still have the logfile.
        pass


def _ensure_streamlit_credentials() -> None:
    """Prevent first-run stdin onboarding prompt in packaged launches."""
    cfg_dir = Path.home() / ".streamlit"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    creds = cfg_dir / "credentials.toml"
    if not creds.is_file():
        creds.write_text('[general]\nemail = ""\n', encoding="utf-8")


def _resolve_app_script() -> Path:
    here = Path(__file__).resolve().parent
    exe_dir = Path(sys.executable).resolve().parent
    meipass = Path(getattr(sys, "_MEIPASS", "")) if getattr(sys, "_MEIPASS", None) else None
    candidates = [
        here / "streamlit_app.py",
        exe_dir / "streamlit_app.py",
        exe_dir / "_internal" / "streamlit_app.py",
    ]
    if meipass is not None:
        candidates.append(meipass / "streamlit_app.py")
    for p in candidates:
        if p.is_file():
            return p
    search_roots = [exe_dir, here]
    if meipass is not None:
        search_roots.append(meipass)
    for root in search_roots:
        try:
            for p in root.rglob("streamlit_app.py"):
                if p.is_file():
                    return p
        except Exception:
            continue
    raise FileNotFoundError(
        "Could not find bundled streamlit_app.py. Tried: "
        + ", ".join(str(p) for p in candidates)
    )


def main() -> int:
    log_path = _logs_dir() / f"startup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
    with log_path.open("w", encoding="utf-8") as logf:
        try:
            app_path = _resolve_app_script()
            logf.write(f"Resolved app path: {app_path}\n")
            os.chdir(app_path.parent)
            logf.write(f"Working directory: {app_path.parent}\n")
            _ensure_streamlit_credentials()
            logf.write("Ensured Streamlit credentials file.\n")
            # Avoid telemetry prompts and keep desktop behavior predictable.
            os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
            os.environ.setdefault("STREAMLIT_GLOBAL_DEVELOPMENT_MODE", "false")
            sys.argv = [
                "streamlit",
                "run",
                str(app_path),
                "--server.headless=false",
                "--browser.gatherUsageStats=false",
                "--server.fileWatcherType=none",
            ]
            with contextlib.redirect_stdout(logf), contextlib.redirect_stderr(logf):
                rc = int(stcli.main())
            if rc != 0:
                _show_error_dialog(
                    "Schedule Builder failed to start",
                    f"Startup exited with code {rc}.\n\nLog file:\n{log_path}",
                )
            return rc
        except Exception:
            logf.write(traceback.format_exc())
            logf.flush()
            err = traceback.format_exc().strip().splitlines()[-1] if traceback.format_exc().strip() else "Unknown error"
            _show_error_dialog(
                "Schedule Builder failed to start",
                f"An error occurred while starting the app.\n\n{err}\n\nLog file:\n{log_path}",
            )
            return 1


if __name__ == "__main__":
    raise SystemExit(main())

