"""Resolve config, catalog, and UI paths for dev, PyInstaller, and installed desktop."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_desktop_runtime() -> bool:
    return os.environ.get("SCHEDULE_BUILDER_DESKTOP_RUNTIME") == "1" or getattr(sys, "frozen", False)


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def executable_dir() -> Path:
    return Path(sys.executable).resolve().parent


def schedule_builder_data_dir() -> Path:
    """Writable per-user data root (install dir for desktop, cwd for dev)."""
    if is_desktop_runtime():
        return executable_dir()
    return Path.cwd()


def local_app_data_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home().as_posix()))
    return base / "ScheduleBuilder"


def resource_search_roots() -> list[Path]:
    """Directories that may contain bundled config/, data/, scheduler-ui/."""
    roots: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        key = str(path.resolve()) if path.exists() else str(path)
        if key not in seen:
            seen.add(key)
            roots.append(path)

    if is_frozen():
        # Installed desktop builds must prefer bundled files over a dev checkout on cwd.
        add(executable_dir())
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            add(Path(meipass))
        internal = executable_dir() / "_internal"
        if internal.is_dir():
            add(internal)
        add(Path.cwd())
    else:
        add(Path.cwd())
        add(executable_dir())
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            add(Path(meipass))
        internal = executable_dir() / "_internal"
        if internal.is_dir():
            add(internal)
    module_root = Path(__file__).resolve().parents[1]
    add(module_root)
    return roots


def _react_dist_index(dist: Path) -> Path | None:
    index = dist / "index.html"
    return dist if index.is_file() else None


def _react_dist_under_install(dist: Path) -> bool:
    if not is_frozen():
        return True
    install_root = executable_dir().resolve()
    try:
        dist.resolve().relative_to(install_root)
        return True
    except ValueError:
        return False


def react_dist_path() -> Path | None:
    env_path = os.environ.get("SCHEDULE_BUILDER_REACT_DIST", "").strip()
    if env_path:
        found = _react_dist_index(Path(env_path))
        if found is not None and _react_dist_under_install(found):
            return found

    if is_frozen():
        install_root = executable_dir()
        for base in (install_root / "_internal", install_root, Path(getattr(sys, "_MEIPASS", "") or "")):
            if not str(base):
                continue
            found = _react_dist_index(base / "scheduler-ui" / "dist")
            if found is not None:
                return found
        return None

    for root in resource_search_roots():
        found = _react_dist_index(root / "scheduler-ui" / "dist")
        if found is not None:
            return found
    return None


def react_dist_bundle_version(dist: Path | None = None) -> str:
    """UI version stamped into scheduler-ui/dist/index.html at build time."""
    target = dist or react_dist_path()
    if target is None:
        return ""
    index_html = target / "index.html"
    if not index_html.is_file():
        return ""
    try:
        text = index_html.read_text(encoding="utf-8")
    except OSError:
        return ""
    marker = 'name="schedule-builder-version" content="'
    start = text.find(marker)
    if start < 0:
        return ""
    start += len(marker)
    end = text.find('"', start)
    if end < 0:
        return ""
    return text[start:end].strip()


def resolve_bundle_file(relative: str, *, extensions: set[str] | None = None) -> Path | None:
    rel = Path(relative)
    names = [rel.name] if rel.name else []
    if rel.parts:
        names.append(rel.as_posix())
    for root in resource_search_roots():
        for name in names:
            candidate = (root / name).resolve()
            if candidate.is_file():
                if extensions and candidate.suffix.lower() not in extensions:
                    continue
                return candidate
            if rel.parts:
                nested = (root / rel).resolve()
                if nested.is_file():
                    if extensions and nested.suffix.lower() not in extensions:
                        continue
                    return nested
    return None


def resolve_config_path(raw: str) -> Path:
    path = Path(raw or "config/april_2026.yaml")
    if path.is_absolute():
        if path.is_file():
            return path
        raise FileNotFoundError(str(path))

    found = resolve_bundle_file(path.as_posix(), extensions={".yaml", ".yml"})
    if found is not None:
        return found

    cwd_candidate = (Path.cwd() / path).resolve()
    if cwd_candidate.is_file():
        return cwd_candidate
    raise FileNotFoundError(str(path))


def imported_catalog_path(cfg_config_file: Path | None = None) -> Path:
    """Writable imported-content store (survives in install dir / AppData)."""
    if is_desktop_runtime():
        target = schedule_builder_data_dir() / "config" / "imported_content_catalog.json"
    elif cfg_config_file is not None:
        config_dir = cfg_config_file.resolve().parent
        repo_root = config_dir.parent if config_dir.name.casefold() == "config" else config_dir
        target = repo_root / "config" / "imported_content_catalog.json"
    else:
        target = Path.cwd() / "config" / "imported_content_catalog.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def catalog_publish_targets() -> list[Path]:
    """JSON catalog files to refresh after import (dev + bundled UI)."""
    targets: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        key = str(path)
        if key in seen:
            return
        seen.add(key)
        targets.append(path)

    dist = react_dist_path()
    if dist is not None:
        add(dist / "content-catalog.json")
    for root in resource_search_roots():
        add(root / "scheduler-ui" / "public" / "content-catalog.json")
        add(root / "scheduler-ui" / "dist" / "content-catalog.json")
    return targets


def saved_schedules_root() -> Path:
    from binge_schedule.app_settings import primary_saved_schedules_root

    return primary_saved_schedules_root()


def default_config_path() -> Path:
    """Active YAML config (demo desktop bundle uses SCHEDULE_BUILDER_DEFAULT_CONFIG)."""
    override = os.environ.get("SCHEDULE_BUILDER_DEFAULT_CONFIG", "").strip()
    if override:
        try:
            return resolve_config_path(override)
        except FileNotFoundError:
            pass
    try:
        return resolve_config_path("config/april_2026.yaml")
    except FileNotFoundError:
        return Path("config/april_2026.yaml")


def desktop_app_version() -> str:
    """Installer/build version (VERSION.txt beside the exe, or DESKTOP_APP_VERSION)."""
    override = os.environ.get("DESKTOP_APP_VERSION", "").strip()
    if override:
        return override
    for root in resource_search_roots():
        version_file = root / "VERSION.txt"
        if version_file.is_file():
            text = version_file.read_text(encoding="utf-8").strip()
            if text:
                return text
    try:
        from binge_schedule import __version__

        return str(__version__).strip()
    except Exception:
        return ""


def content_import_wizard_available() -> bool:
    try:
        import multipart  # noqa: F401
    except ImportError:
        return False
    try:
        import binge_schedule.content_import_wizard  # noqa: F401
        import binge_schedule.content_import  # noqa: F401
    except ImportError:
        return False
    return True
