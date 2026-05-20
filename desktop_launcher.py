"""Windows desktop launcher for Schedule Builder.

Built with PyInstaller (one-folder mode). Starts the React UI on a local API
and opens it in a native desktop window (splash video, then the app).
Falls back to Streamlit or the default browser when the React bundle is missing.
"""

from __future__ import annotations

import contextlib
import os
import sys
import threading
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


def _resolve_react_dist() -> Path | None:
    here = Path(__file__).resolve().parent
    exe_dir = Path(sys.executable).resolve().parent
    meipass = Path(getattr(sys, "_MEIPASS", "")) if getattr(sys, "_MEIPASS", None) else None
    candidates = [
        here / "scheduler-ui" / "dist",
        exe_dir / "scheduler-ui" / "dist",
        exe_dir / "_internal" / "scheduler-ui" / "dist",
    ]
    if meipass is not None:
        candidates.append(meipass / "scheduler-ui" / "dist")
    for p in candidates:
        if (p / "index.html").is_file():
            return p
    return None


def _run_react_api_server() -> None:
    import uvicorn

    uvicorn.run("binge_schedule.api:app", host="127.0.0.1", port=8765, log_level="info")


def _open_react_desktop_window(logf) -> int:
    from binge_schedule.app_settings import load_settings
    from binge_schedule.desktop_window import open_native_window, wait_for_api

    base_url = "http://127.0.0.1:8765"
    splash_url = f"{base_url}/splash.html"
    window_mode = str(load_settings().get("desktop_window_mode") or "windowed")
    server = threading.Thread(target=_run_react_api_server, daemon=True)
    server.start()
    logf.write("Started API server thread.\n")
    if not wait_for_api(base_url):
        raise RuntimeError("Schedule Builder API did not start on port 8765.")
    logf.write("API health check passed.\n")
    logf.write(f"Desktop window mode: {window_mode}\n")
    try:
        open_native_window(splash_url=splash_url, window_mode=window_mode)
        logf.write("Desktop window closed.\n")
        return 0
    except RuntimeError as exc:
        logf.write(f"Native window unavailable ({exc}); falling back to default browser.\n")
        import webbrowser

        threading.Timer(1.2, lambda: webbrowser.open(splash_url)).start()
        _run_react_api_server()
        return 0


def _desktop_working_directory(react_dist: Path | None) -> Path:
    """Use the install/exe folder so bundled config/ and writable config/ resolve correctly."""
    exe_dir = Path(sys.executable).resolve().parent
    if react_dist is not None:
        for root in (exe_dir, react_dist.parent.parent, react_dist.parent.parent.parent):
            if (root / "config").is_dir() or (root / "scheduler-ui").is_dir():
                return root
    return exe_dir


def main() -> int:
    log_path = _logs_dir() / f"startup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
    with log_path.open("w", encoding="utf-8") as logf:
        try:
            react_dist = _resolve_react_dist()
            if react_dist is not None:
                root = _desktop_working_directory(react_dist)
                os.chdir(root)
                logf.write(f"Resolved React UI path: {react_dist}\n")
                logf.write(f"Working directory: {root}\n")
                os.environ.setdefault("SCHEDULE_BUILDER_DESKTOP_RUNTIME", "1")
                os.environ.setdefault("SCHEDULE_BUILDER_REACT_DIST", str(react_dist))
                demo_schedule = (
                    root / "saved_schedules" / "test" / "2026-05-19_21-33-48" / "base_schedule.yaml"
                )
                if demo_schedule.is_file():
                    os.environ.setdefault("SCHEDULE_BUILDER_DEFAULT_CONFIG", "config/blank_schedule.yaml")
                with contextlib.redirect_stdout(logf), contextlib.redirect_stderr(logf):
                    return _open_react_desktop_window(logf)

            app_path = _resolve_app_script()
            logf.write(f"Resolved app path: {app_path}\n")
            os.chdir(app_path.parent)
            logf.write(f"Working directory: {app_path.parent}\n")
            _ensure_streamlit_credentials()
            logf.write("Ensured Streamlit credentials file.\n")
            # Desktop installs should not show the desktop download CTA.
            os.environ.setdefault("SCHEDULE_BUILDER_DESKTOP_RUNTIME", "1")
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

