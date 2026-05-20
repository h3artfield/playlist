"""Native desktop window (pywebview) for Schedule Builder."""

from __future__ import annotations

import os
import socket
import time
import urllib.error
import urllib.request


def api_health_ok(base_url: str, *, timeout: float = 0.75) -> bool:
    health_url = f"{base_url.rstrip('/')}/api/health"
    try:
        with urllib.request.urlopen(health_url, timeout=timeout) as response:
            if response.status != 200:
                return False
            body = response.read(400).decode("utf-8", errors="ignore")
            return '"status"' in body and '"ok"' in body
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def port_is_listening(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.35)
        return sock.connect_ex((host, port)) == 0


def pick_api_port(*, preferred: int = 8765, span: int = 20) -> int:
    """Reuse a healthy API or pick the first free port (fast scan)."""
    host = "127.0.0.1"
    if api_health_ok(f"http://{host}:{preferred}"):
        return preferred
    if not port_is_listening(host, preferred):
        return preferred
    for port in range(preferred + 1, preferred + span):
        if api_health_ok(f"http://{host}:{port}"):
            return port
        if not port_is_listening(host, port):
            return port
    return preferred


def wait_for_api(base_url: str, *, timeout_seconds: float = 60.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if api_health_ok(base_url):
            return True
        time.sleep(0.2)
    return False


def _normalize_mode(mode: str) -> str:
    cleaned = str(mode or "windowed").strip().lower()
    return cleaned if cleaned in {"fullscreen", "windowed"} else "windowed"


def apply_desktop_window_mode(mode: str) -> bool:
    """Switch the running native window between fullscreen and resizable windowed."""
    try:
        import webview
    except ImportError:
        return False

    if not webview.windows:
        return False

    window = webview.windows[0]
    target = _normalize_mode(mode)
    try:
        if target == "fullscreen":
            if not window.fullscreen:
                window.toggle_fullscreen()
        elif window.fullscreen:
            window.toggle_fullscreen()
        return True
    except Exception:
        return False


def open_native_window(
    *,
    splash_url: str,
    window_mode: str = "windowed",
    min_width: int = 1100,
    min_height: int = 700,
) -> None:
    try:
        import webview
    except ImportError as exc:
        raise RuntimeError(
            "Native desktop window requires pywebview. Install with: python -m pip install pywebview"
        ) from exc

    mode = _normalize_mode(window_mode)
    use_fullscreen = mode == "fullscreen"

    window = webview.create_window(
        "Schedule Builder",
        splash_url,
        width=1280,
        height=800,
        min_size=(min_width, min_height),
        resizable=not use_fullscreen,
        fullscreen=use_fullscreen,
        text_select=True,
        zoomable=False,
    )

    def on_closed() -> None:
        is_desktop = os.environ.get("SCHEDULE_BUILDER_DESKTOP_RUNTIME") == "1"
        if is_desktop:
            os._exit(0)

    window.events.closed += on_closed
    webview.start(private_mode=False, debug=False)
