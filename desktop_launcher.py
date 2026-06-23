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
API_PORT = 8765  # default; desktop may use 8766+ if 8765 is stuck


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


def _run_react_api_server(port: int) -> None:
    import uvicorn

    uvicorn.run("binge_schedule.api:app", host=API_HOST, port=port, log_level="warning")


def _prepare_api(logf) -> str:
    """Pick a port and start the API in the background. The UI opens immediately."""
    from binge_schedule.desktop_window import api_health_ok, pick_api_port
    from binge_schedule.runtime_paths import desktop_app_version, react_dist_bundle_version, react_dist_path

    expected_version = desktop_app_version()
    expected_ui_version = react_dist_bundle_version(react_dist_path())
    port = pick_api_port(
        preferred=API_PORT,
        expected_version=expected_version,
        expected_ui_version=expected_ui_version,
    )
    base_url = f"http://{API_HOST}:{port}"
    logf.write(f"API port: {port}\n")
    if expected_version:
        logf.write(f"Expected app version: {expected_version}\n")
    if expected_ui_version:
        logf.write(f"Expected UI bundle version: {expected_ui_version}\n")

    if api_health_ok(
        base_url,
        expected_version=expected_version,
        expected_ui_version=expected_ui_version,
    ):
        logf.write(f"Reusing API already listening on port {port}.\n")
        return base_url

    server = threading.Thread(target=_run_react_api_server, args=(port,), daemon=True)
    server.start()
    logf.write(f"Started API server thread on port {port} (window opens while loading).\n")
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

    base_url = _prepare_api(logf)
    splash_url = f"{base_url}/splash.html"
    window_mode = str(load_settings().get("desktop_window_mode") or "windowed")
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
            if _is_packaged():
                from binge_schedule.runtime_paths import executable_dir

                os.chdir(executable_dir())
                logf.write(f"Working directory set to install dir: {executable_dir()}\n")
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
            # Desktop builds use import-only catalog (no bundled Nikki/archive shows).
            os.environ.setdefault("SCHEDULE_BUILDER_DEFAULT_CONFIG", "config/desktop.yaml")
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
