"""Windows desktop launcher for Schedule Builder.

Packaged builds always use the bundled React UI in a native desktop window.
Streamlit is not used for the installed desktop app.
"""

from __future__ import annotations

import contextlib
import os
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path

API_HOST = "127.0.0.1"
API_PORT = 8765


def _logs_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home().as_posix()))
    p = base / "ScheduleBuilder" / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _is_packaged() -> bool:
    return getattr(sys, "frozen", False)


def _acquire_single_instance() -> bool:
    """Return False if another Schedule Builder process already holds the mutex."""
    if sys.platform != "win32":
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        mutex = kernel32.CreateMutexW(None, False, "Local\\ScheduleBuilder.SingleInstance")
        already_running = kernel32.GetLastError() == 183
        if already_running:
            _show_error_dialog(
                "Schedule Builder",
                "Schedule Builder is already running.\n\nClose the other window first, then try again.",
            )
            return False
    except Exception:
        return True
    return True


def _show_error_dialog(title: str, message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        pass


def _resolve_react_dist() -> Path | None:
    from binge_schedule.runtime_paths import react_dist_path

    return react_dist_path()


def _react_missing_message() -> str:
    from binge_schedule.runtime_paths import resource_search_roots

    roots = ", ".join(str(p) for p in resource_search_roots())
    return (
        "The React Schedule Builder UI is missing from this install.\n\n"
        f"Searched under: {roots}\n\n"
        "Reinstall from the latest ScheduleBuilderSetup.exe build. "
        "If you built locally, run scheduler-ui npm build before packaging."
    )


def _run_react_api_server() -> None:
    import uvicorn

    uvicorn.run("binge_schedule.api:app", host=API_HOST, port=API_PORT, log_level="info")


def _ensure_api_running(logf) -> str:
    from binge_schedule.desktop_window import (
        api_health_ok,
        free_port_on_windows,
        port_is_listening,
        wait_for_api,
    )

    base_url = f"http://{API_HOST}:{API_PORT}"

    if api_health_ok(base_url):
        logf.write("Reusing API already listening on port 8765.\n")
        return base_url

    if port_is_listening(API_HOST, API_PORT):
        from binge_schedule.desktop_window import _listeners_on_port

        pids = _listeners_on_port(API_PORT)
        logf.write(f"Port 8765 is in use (listener PIDs: {pids or 'unknown'}).\n")
        logf.write("Attempting to stop prior Schedule Builder / dev API...\n")
        aggressive = os.environ.get("SCHEDULE_BUILDER_DESKTOP_RUNTIME") == "1"
        if free_port_on_windows(API_PORT, aggressive=aggressive):
            logf.write("Freed port 8765.\n")
        elif api_health_ok(base_url):
            logf.write("Port in use but Schedule Builder API health check passed; reusing it.\n")
            return base_url
        else:
            raise RuntimeError(
                "Port 8765 is still in use. Close any Schedule Builder window, stop the dev API "
                "(scripts/start-dev-api.ps1), or run: "
                "Get-NetTCPConnection -LocalPort 8765 -State Listen | "
                "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }"
            )

    server = threading.Thread(target=_run_react_api_server, daemon=True)
    server.start()
    logf.write("Started API server thread.\n")
    if not wait_for_api(base_url):
        raise RuntimeError(
            "Schedule Builder API did not start on port 8765. "
            "See the log file in %LOCALAPPDATA%\\ScheduleBuilder\\logs\\"
        )
    return base_url


def _desktop_working_directory(react_dist: Path) -> Path:
    from binge_schedule.runtime_paths import executable_dir

    exe_dir = executable_dir()
    for root in (exe_dir, react_dist.parent.parent, react_dist.parent.parent.parent):
        if (root / "config").is_dir() or (root / "scheduler-ui").is_dir():
            return root
    return exe_dir


def _open_react_desktop_window(logf) -> int:
    from binge_schedule.app_settings import load_settings
    from binge_schedule.desktop_window import open_native_window

    base_url = _ensure_api_running(logf)
    splash_url = f"{base_url}/splash.html"
    window_mode = str(load_settings().get("desktop_window_mode") or "windowed")
    logf.write("API health check passed.\n")
    logf.write(f"Desktop window mode: {window_mode}\n")
    open_native_window(splash_url=splash_url, window_mode=window_mode)
    logf.write("Desktop window closed.\n")
    return 0


def _run_streamlit_dev_fallback(logf) -> int:
    """Legacy Streamlit UI — development only when React dist is not built."""
    from streamlit.web import cli as stcli

    here = Path(__file__).resolve().parent
    app_path = here / "streamlit_app.py"
    if not app_path.is_file():
        app_path = Path.cwd() / "streamlit_app.py"
    if not app_path.is_file():
        raise FileNotFoundError("streamlit_app.py not found for dev fallback.")

    logf.write(f"Dev fallback: Streamlit at {app_path}\n")
    os.chdir(app_path.parent)
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
    return int(stcli.main())


def main() -> int:
    if not _acquire_single_instance():
        return 0

    log_path = _logs_dir() / f"startup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
    with log_path.open("w", encoding="utf-8") as logf:
        try:
            os.environ.setdefault("SCHEDULE_BUILDER_DESKTOP_RUNTIME", "1")
            react_dist = _resolve_react_dist()
            logf.write(f"Packaged build: {_is_packaged()}\n")
            logf.write(f"Executable: {sys.executable}\n")

            if react_dist is None:
                logf.write("React dist not found.\n")
                if _is_packaged():
                    message = _react_missing_message()
                    logf.write(message + "\n")
                    _show_error_dialog("Schedule Builder failed to start", f"{message}\n\nLog file:\n{log_path}")
                    return 1
                with contextlib.redirect_stdout(logf), contextlib.redirect_stderr(logf):
                    return _run_streamlit_dev_fallback(logf)

            root = _desktop_working_directory(react_dist)
            os.chdir(root)
            logf.write(f"Resolved React UI path: {react_dist}\n")
            logf.write(f"Working directory: {root}\n")
            os.environ.setdefault("SCHEDULE_BUILDER_REACT_DIST", str(react_dist))
            demo_schedule = root / "saved_schedules" / "test" / "2026-05-19_21-33-48" / "base_schedule.yaml"
            if demo_schedule.is_file():
                os.environ.setdefault("SCHEDULE_BUILDER_DEFAULT_CONFIG", "config/blank_schedule.yaml")

            with contextlib.redirect_stdout(logf), contextlib.redirect_stderr(logf):
                return _open_react_desktop_window(logf)
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
