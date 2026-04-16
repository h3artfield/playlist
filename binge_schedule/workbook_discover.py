"""Discover content-workbook tabs for the archive UI (playlist entries + Excel tabs not on the playlist yet)."""

from __future__ import annotations

import re

from binge_schedule.models import BuildConfig, ShowDef

# Streamlit / UI: internal select value prefix (not a YAML show key).
WORKBOOK_TAB_PREFIX = "__workbook_tab__::"


def is_movies_tab(sheet_name: str) -> bool:
    return sheet_name.strip().casefold() == "movies"


def series_nikki_sheets_used(cfg: BuildConfig) -> set[str]:
    return {sd.nikki_sheet for sd in cfg.shows.values() if sd.kind == "series" and sd.nikki_sheet}


def workbook_tabs_not_in_yaml(cfg: BuildConfig, sheet_names: tuple[str, ...]) -> list[str]:
    """Excel tabs to list for browsing: not the ``movies`` catalog and not already used as a playlist series tab."""
    used = series_nikki_sheets_used(cfg)
    out: list[str] = []
    for s in sheet_names:
        if is_movies_tab(s):
            continue
        if s in used:
            continue
        out.append(s)
    return sorted(out, key=str.casefold)


def workbook_tab_option(sheet_name: str) -> str:
    return f"{WORKBOOK_TAB_PREFIX}{sheet_name}"


def parse_workbook_tab_option(opt: str) -> str | None:
    if not opt.startswith(WORKBOOK_TAB_PREFIX):
        return None
    return opt[len(WORKBOOK_TAB_PREFIX) :]


def synthetic_series_for_tab(sheet_name: str) -> ShowDef:
    """Minimal ``ShowDef`` for browsing an Excel tab that is not on the playlist setup yet."""
    pfx = _guess_prefix(sheet_name)
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", sheet_name).strip("_").lower()[:50] or "tab"
    return ShowDef(
        key=f"_workbook_{slug}",
        display_name=sheet_name.strip(),
        kind="series",
        nikki_sheet=sheet_name,
        prefix=pfx,
    )


def _guess_prefix(sheet_name: str) -> str:
    al = re.sub(r"[^A-Za-z0-9]", "", sheet_name)
    return (al[:3] or "ZZZ").upper()
