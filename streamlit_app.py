"""
Schedule Builder — Streamlit UI to build BINGE exports, browse the content archive, and edit schedule sources.

Run from the project directory:
  streamlit run streamlit_app.py
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import platform
import shutil
import subprocess
import tempfile
from dataclasses import asdict
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, List, Optional

import pandas as pd
import streamlit as st

from binge_schedule import nikki
from binge_schedule.archive_normalize import normalize_episodes_for_archive
from binge_schedule.binge_overrides import BingeRowOverride, parse_flexible_time
from binge_schedule.config_io import load_build_config
from binge_schedule.models import NikkiColumnHeaders, ShowDef
from binge_schedule.cursor_state import resolved_cursor_state_path, resolved_nikki_workbook_path
from binge_schedule.binge_to_grid import normalize_binge_df_columns
from binge_schedule.export_xlsx import export_both, is_verbose_seed_noise
from binge_schedule.show_swap import apply_show_swap, parse_schedule_anchor
from binge_schedule.show_resolve import resolve_show
from binge_schedule.grid import (
    day_dates,
    ensure_grids_workbooks_for_weeks,
    load_grid_sheet,
    parse_monday,
    parse_sheet_tab_monday,
    segments_for_day,
    slot_label,
    weeks_with_monday_in_calendar_month,
)
from binge_schedule.workbook_discover import (
    parse_workbook_tab_option,
    synthetic_series_for_tab,
    workbook_tabs_not_in_yaml,
    workbook_tab_option,
)


def _default_config_display() -> str:
    raw = (os.environ.get("BINGE_CONFIG_PATH") or os.environ.get("STREAMLIT_BINGE_CONFIG") or "").strip()
    if raw:
        return Path(raw).as_posix()
    april = Path("config/april_2026.yaml")
    if april.is_file():
        return april.as_posix()
    return Path("config/cloud.yaml").as_posix()


def _open_folder(path: Path) -> str:
    p = path.resolve()
    if not p.is_dir():
        return f"Folder not found: {p}"
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.Popen(["explorer.exe", str(p)], close_fds=True)
        elif system == "Darwin":
            subprocess.Popen(["open", str(p)], close_fds=True)
        else:
            opener = shutil.which("xdg-open")
            if not opener:
                return (
                    "Opening a folder isn’t available on this system (e.g. Streamlit Cloud or a phone). "
                    "Use the **BINGE.xlsx** / **BINGE GRIDS.xlsx** download buttons."
                )
            subprocess.Popen([opener, str(p)], close_fds=True)
    except OSError:
        return (
            "Couldn’t open the folder automatically. "
            "On Streamlit Cloud or mobile, use the download buttons to save the files."
        )
    return ""


def _nikki_sheet_exists(workbook: Path, sheet: str | None) -> bool | None:
    if not workbook.is_file() or not sheet:
        return None
    try:
        import openpyxl

        wb = openpyxl.load_workbook(workbook, read_only=True)
        ok = sheet in wb.sheetnames
        wb.close()
        return ok
    except OSError:
        return None


def _add_one_month(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def _months_for_build_selector(weeks: list) -> list[date]:
    """Months from the earliest ``weeks`` Monday through the month *after* the latest Monday.

    The extra month (e.g. May when only April has ``weeks:``) is the usual **next** build target;
    episode cursors already reflect April after you run April—May still needs its own ``weeks:`` lines.
    The month anchor is still used for unlock sequencing, but actual builds use Start date + week count.
    """
    dates: list[date] = []
    for w in weeks:
        try:
            dates.append(date.fromisoformat(w.monday))
        except ValueError:
            continue
    if not dates:
        return []
    dmin, dmax = min(dates), max(dates)
    start = date(dmin.year, dmin.month, 1)
    end_inclusive = _add_one_month(date(dmax.year, dmax.month, 1))
    out: list[date] = []
    cur = start
    while cur <= end_inclusive:
        out.append(cur)
        cur = _add_one_month(cur)
    return out


def _weeks_in_month(weeks: list, month_start: date) -> list:
    """Weeks whose **Monday** is in this calendar month (first Monday = start of that month’s report).

    Does **not** include the prior month’s straddle week (e.g. 2026-04-27 when building May).
    """
    y, m = month_start.year, month_start.month
    return weeks_with_monday_in_calendar_month(weeks, y, m)


def _regenerate_binge_for_month(
    cfg_path: Path, schedule_anchor: Any
) -> tuple[bool, list[str], Optional[tuple[Path, Path, Path]]]:
    """After a grid swap, rebuild BINGE + GRIDS for the calendar month that contains the anchor date."""
    parsed = parse_schedule_anchor(schedule_anchor)
    if not parsed:
        return False, [], None
    d, _ = parsed
    month_start = date(d.year, d.month, 1)
    cfg = load_build_config(cfg_path)
    weeks = _weeks_in_month(cfg.weeks, month_start)
    if not weeks:
        return (
            False,
            [
                f"No **weeks:** for **{month_start.strftime('%B %Y')}** — automatic BINGE export was skipped."
            ],
            None,
        )
    nikki_path = resolved_nikki_workbook_path(cfg)
    if not nikki_path.is_file():
        return (
            False,
            [f"Nikki workbook not found — automatic export skipped: `{nikki_path}`"],
            None,
        )
    missing_grids: list[str] = []
    for w in weeks:
        if not Path(w.grids_file).is_file():
            missing_grids.append(str(Path(w.grids_file)))
    if missing_grids:
        return (
            False,
            ["Grids file missing — automatic export skipped:"]
            + [f"- `{p}`" for p in missing_grids],
            None,
        )
    try:
        created = ensure_grids_workbooks_for_weeks(weeks)
    except (OSError, ValueError) as e:
        return False, [f"Could not prepare grids: {e}"], None

    out_dir = Path(tempfile.mkdtemp(prefix="binge_after_swap_"))
    station_kw: Optional[List[str]] = None
    if cfg.export_stations:
        station_kw = list(cfg.export_stations)
    try:
        binge_path, grids_path, ovw, seeded = export_both(
            cfg, out_dir, weeks=weeks, export_stations=station_kw
        )
    except Exception as e:
        return False, [f"**Create BINGE files** failed after swap: {e}"], None

    msgs: list[str] = [
        f"Automatically regenerated **BINGE.xlsx** and **BINGE GRIDS.xlsx** for **{month_start.strftime('%B %Y')}** "
        f"({len(weeks)} week tab(s)) — use the downloads below."
    ]
    if created:
        msgs.append("Created grids shell(s): " + ", ".join(f"`{p}`" for p in created))
    for w in ovw:
        msgs.append(str(w))
    for s in seeded:
        if is_verbose_seed_noise(s):
            continue
        msgs.append(s)
    return True, msgs, (binge_path, grids_path, out_dir)


@lru_cache(maxsize=1)
def _streamlit_container_supports_border() -> bool:
    return "border" in inspect.signature(st.container).parameters


@lru_cache(maxsize=1)
def _dataframe_row_selection_supported() -> bool:
    sig = inspect.signature(st.dataframe)
    return "on_select" in sig.parameters and "selection_mode" in sig.parameters


def _archive_detail_panel():
    if _streamlit_container_supports_border():
        return st.container(border=True)
    return st.container()


def _nikki_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return -1.0


def _archive_wkey(sel: str) -> str:
    return hashlib.sha256(sel.encode("utf-8")).hexdigest()[:26]


def _mobile_styles() -> None:
    """Inject once: top-nav layout, stack-friendly columns, tap targets."""
    st.markdown(
        """
        <style>
        /* Top navigation: hide sidebar — nav is the segmented control below the title */
        [data-testid="stSidebar"] {
            display: none !important;
        }
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        section[data-testid="stMain"] > div {
            margin-left: 0 !important;
        }
        .main .block-container {
            padding-top: 0.75rem !important;
            max-width: 42rem !important;
        }
        @media (max-width: 768px) {
            .block-container {
                padding-left: max(12px, env(safe-area-inset-left)) !important;
                padding-right: max(12px, env(safe-area-inset-right)) !important;
            }
            [data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
                gap: 0.5rem !important;
            }
            [data-testid="stHorizontalBlock"] > [data-testid="column"] {
                flex: 1 1 100% !important;
                min-width: unset !important;
                width: 100% !important;
            }
        }
        button[kind="primary"], button[kind="secondary"], .stDownloadButton button {
            min-height: 2.75rem;
        }
        /* Primary actions + downloads: green (was default Streamlit red primary) */
        button[kind="primary"],
        .stDownloadButton button,
        div[data-testid="stDownloadButton"] button {
            background-color: #16a34e !important;
            background-image: none !important;
            border-color: #15803d !important;
            color: #ffffff !important;
        }
        button[kind="primary"]:hover,
        .stDownloadButton button:hover,
        div[data-testid="stDownloadButton"] button:hover {
            background-color: #15803d !important;
            border-color: #166534 !important;
            color: #ffffff !important;
        }
        button[kind="primary"]:focus-visible,
        .stDownloadButton button:focus-visible,
        div[data-testid="stDownloadButton"] button:focus-visible {
            box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.5) !important;
        }
        /* Segmented nav: Streamlit uses stButtonGroup (radio + aria-checked), not stSegmentedControl */
        div[data-testid="stButtonGroup"],
        div[data-testid="stSegmentedControl"] {
            width: 100%;
        }
        div[data-testid="stButtonGroup"] button,
        div[data-testid="stSegmentedControl"] button {
            border-style: solid !important;
            border-radius: 12px !important;
            transition: border-width 0.12s ease, border-color 0.12s ease, background-color 0.12s ease !important;
        }
        div[data-testid="stButtonGroup"] button[aria-checked="false"],
        div[data-testid="stButtonGroup"] button[aria-pressed="false"],
        div[data-testid="stSegmentedControl"] button[aria-pressed="false"] {
            border-width: 1px !important;
            border-color: rgba(255, 255, 255, 0.22) !important;
            background-color: transparent !important;
            background-image: none !important;
        }
        /* Selected segment: green (default “primary” / checked state is red) */
        div[data-testid="stButtonGroup"] button[aria-checked="true"],
        div[data-testid="stButtonGroup"] button[aria-pressed="true"],
        div[data-testid="stButtonGroup"] button[aria-selected="true"],
        div[data-testid="stSegmentedControl"] button[aria-pressed="true"],
        div[data-testid="stSegmentedControl"] button[aria-checked="true"],
        div[data-testid="stSegmentedControl"] button[aria-selected="true"],
        div[data-testid="stSegmentedControl"] [role="option"][aria-selected="true"] {
            border-width: 3px !important;
            border-color: #22c55e !important;
            background-color: #15803d !important;
            background-image: none !important;
            color: #ffffff !important;
        }
        div[data-testid="stButtonGroup"] button[aria-checked="true"] *,
        div[data-testid="stButtonGroup"] button[aria-pressed="true"] *,
        div[data-testid="stSegmentedControl"] button[aria-pressed="true"] *,
        div[data-testid="stSegmentedControl"] button[aria-checked="true"] * {
            color: #ffffff !important;
        }
        div[data-testid="stButtonGroup"] button[aria-checked="true"]:hover,
        div[data-testid="stButtonGroup"] button[aria-pressed="true"]:hover,
        div[data-testid="stSegmentedControl"] button[aria-pressed="true"]:hover,
        div[data-testid="stSegmentedControl"] button[aria-checked="true"]:hover {
            background-color: #166534 !important;
            border-color: #4ade80 !important;
            color: #ffffff !important;
        }
        /* Horizontal radio fallback: thick border on chosen option */
        div[data-testid="stRadio"] > div {
            gap: 0.5rem !important;
            flex-wrap: wrap !important;
        }
        div[data-testid="stRadio"] label {
            border-radius: 12px !important;
            padding: 0.45rem 0.75rem !important;
            border: 1px solid rgba(255, 255, 255, 0.22) !important;
        }
        div[data-testid="stRadio"] label:has(input:checked) {
            border-width: 3px !important;
            border-color: #22c55e !important;
            background-color: rgba(34, 197, 94, 0.18) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


_NAV_BUILD = "Build schedule"
_NAV_ARCHIVE = "View content archive"
_NAV_EDIT_SCHEDULE = "Edit schedules"
_MAIN_NAV_OPTIONS = (_NAV_BUILD, _NAV_ARCHIVE, _NAV_EDIT_SCHEDULE)
_LEGACY_MAIN_NAV_TAB: dict[str, str] = {
    "Build": _NAV_BUILD,
    "Build playlist": _NAV_BUILD,
    "Content archive": _NAV_ARCHIVE,
    "Playlist": _NAV_EDIT_SCHEDULE,
    "Edit playlist": _NAV_EDIT_SCHEDULE,
    "Edit playlists": _NAV_EDIT_SCHEDULE,
}
# Must not assign to ``main_nav_tabs`` after the segmented control renders — use ``main_nav_pending`` + rerun instead.
_MAIN_NAV_PENDING_KEY = "main_nav_pending"


def _coerce_main_nav_value(val: Any) -> str | None:
    if val is None:
        return None
    s = str(val)
    if s in _MAIN_NAV_OPTIONS:
        return s
    return _LEGACY_MAIN_NAV_TAB.get(s)


def _render_top_nav() -> str:
    """Primary section switcher — top bar (replaces sidebar nav). Returns selected page name."""
    cur = st.session_state.get("main_nav_tabs")
    coerced = _coerce_main_nav_value(cur)
    if cur is not None and coerced is not None:
        st.session_state["main_nav_tabs"] = coerced
    elif cur is not None and coerced is None:
        st.session_state["main_nav_tabs"] = _NAV_BUILD

    pending_raw = st.session_state.pop(_MAIN_NAV_PENDING_KEY, None)
    pending = _coerce_main_nav_value(pending_raw)
    if pending in _MAIN_NAV_OPTIONS:
        st.session_state["main_nav_tabs"] = pending

    if st.session_state.get("main_nav_tabs") not in _MAIN_NAV_OPTIONS:
        st.session_state["main_nav_tabs"] = _NAV_BUILD

    nav_col, setup_col = st.columns([5, 1], vertical_alignment="center")
    with nav_col:
        if hasattr(st, "segmented_control"):
            page = st.segmented_control(
                "Section",
                options=_MAIN_NAV_OPTIONS,
                default=_NAV_BUILD,
                key="main_nav_tabs",
                label_visibility="collapsed",
                width="stretch",
            )
        else:
            page = st.radio(
                "Section",
                _MAIN_NAV_OPTIONS,
                horizontal=True,
                key="main_nav_tabs",
                label_visibility="collapsed",
            )
    with setup_col:
        if "main_setup_yaml" not in st.session_state:
            st.session_state["main_setup_yaml"] = _default_config_display()
        if hasattr(st, "popover"):
            with st.popover("Setup", use_container_width=True):
                st.text_input(
                    "Schedule setup (YAML)",
                    key="main_setup_yaml",
                    placeholder="config/april_2026.yaml",
                )
        else:
            st.text_input(
                "Setup file",
                key="main_setup_yaml",
                placeholder="config/april_2026.yaml",
                label_visibility="collapsed",
            )
    if page is None:
        return _NAV_BUILD
    return str(page)


@st.cache_data(show_spinner=False)
def _nikki_workbook_sheet_names(workbook_resolved: str, _mtime: float) -> tuple[str, ...]:
    import openpyxl

    wb = openpyxl.load_workbook(workbook_resolved, read_only=True)
    try:
        return tuple(wb.sheetnames)
    finally:
        wb.close()


def _nikki_headers_from_json(blob: str) -> NikkiColumnHeaders:
    raw = json.loads(blob)
    if not raw:
        return NikkiColumnHeaders.standard_series()
    return NikkiColumnHeaders(
        episode=raw.get("episode") or "Episode",
        season_episode=raw.get("season_episode"),
        year=raw.get("year"),
        stars=raw.get("stars"),
        synopsis=raw.get("synopsis"),
    )


@st.cache_data(show_spinner="Loading episodes from workbook…")
def _archive_sheet_episodes(
    workbook: str,
    _workbook_mtime: float,
    sheet: str,
    style: str,
    prefix: str,
    row_filter: Optional[str],
    headers_json: str,
) -> list[dict[str, Any]]:
    columns = _nikki_headers_from_json(headers_json)
    eps = nikki.load_sheet(
        workbook,
        sheet,
        style=style,
        prefix=prefix,
        columns=columns,
        row_filter=row_filter,
    )
    return normalize_episodes_for_archive(eps, style)


def _render_archive_episode_browser(
    sel: str,
    sd: ShowDef,
    nikki_path: Path,
    *,
    style: str,
    hdrs: NikkiColumnHeaders,
    sheet_ok: bool | None,
    browse_only: bool = False,
) -> None:
    st.markdown("### Episodes")
    if browse_only:
        st.caption(
            "Browse only — not on the schedule until you add this tab under **`nikki_sheet`** in your setup. "
            "**Create BINGE files** skips it until then."
        )
    if sd.nikki_row_filter == nikki.ROW_FILTER_GREEN_EPISODE_CELL:
        st.caption(
            "Only **green** Episode cells count (same rule as **Create BINGE files**); other rows on this sheet are ignored."
        )
    elif sd.nikki_row_filter:
        st.caption(
            f"Row filter `{sd.nikki_row_filter}` — table matches what **Create BINGE files** would load."
        )
    if not nikki_path.is_file():
        st.warning("Spreadsheet file not found — check **nikki_workbook** in your setup.")
        return
    if not sd.nikki_sheet:
        st.info("This show has no **nikki_sheet**; there is no Excel tab to list.")
        return
    if sheet_ok is False:
        st.error(
            "Your workbook has no tab with this exact name. Fix **nikki_sheet** in the setup or rename the tab in Excel."
        )
        return
    if sheet_ok is None:
        st.warning("Could not verify the tab name against the workbook file.")
    wb_abs = str(nikki_path.resolve())
    mtime = _nikki_mtime(nikki_path)
    headers_json = json.dumps(asdict(hdrs), sort_keys=True)
    try:
        rows = _archive_sheet_episodes(
            wb_abs,
            mtime,
            sd.nikki_sheet,
            style,
            sd.prefix or "",
            sd.nikki_row_filter,
            headers_json,
        )
    except Exception as e:
        st.error(f"Could not read this tab: {e}")
        return
    if not rows:
        if sd.nikki_row_filter == nikki.ROW_FILTER_GREEN_EPISODE_CELL:
            st.warning(
                "**No green Episode cells matched.** **Create BINGE files** would also get an empty list for this "
                "show—confirm playable rows use the expected green fill on the Episode column, and that "
                "**nikki_workbook** points at the real file (not a placeholder)."
            )
        else:
            st.info("No episode rows were parsed (check the header row and column titles on this tab).")
        return

    st.caption(
        f"**{len(rows)}** rows — schedule **#** column matches **Create BINGE files**"
        + (" (when on the schedule)." if not browse_only else " (browse only until added to setup).")
        + " Click a row for detail."
    )

    seasons_found = sorted({r["season"] for r in rows if r["season"] is not None})
    has_unnumbered = any(r["season"] is None for r in rows)
    season_opts = ["All seasons"]
    season_opts.extend(f"Season {s}" for s in seasons_found)
    if has_unnumbered and seasons_found:
        season_opts.append("Unnumbered / list order")

    pick_season = st.selectbox(
        "Season filter",
        season_opts,
        key=f"archive_season_{_archive_wkey(sel)}",
    )
    q = st.text_input(
        "Search",
        "",
        key=f"archive_search_{_archive_wkey(sel)}",
        placeholder="Title, code, or cell text…",
    )

    def season_match(r: dict[str, Any]) -> bool:
        if pick_season == "All seasons":
            return True
        if pick_season.startswith("Season "):
            sn = int(pick_season.replace("Season ", ""))
            return r["season"] == sn
        if pick_season == "Unnumbered / list order":
            return r["season"] is None
        return True

    qn = q.strip().casefold()

    def search_match(r: dict[str, Any]) -> bool:
        if not qn:
            return True
        for fld in ("title", "code", "raw_cell", "sheet_se"):
            if qn in str(r.get(fld, "")).casefold():
                return True
        return False

    filtered = [r for r in rows if season_match(r) and search_match(r)]
    if not filtered:
        st.warning("No episodes match the current season filter and search.")
        return

    disp = pd.DataFrame(
        {
            "#": [r["schedule_num"] for r in filtered],
            "S×E": [r["se_compact"] for r in filtered],
            "Season": [("—" if r["season"] is None else str(r["season"])) for r in filtered],
            "Ep": [("—" if r["ep_in_season"] is None else str(r["ep_in_season"])) for r in filtered],
            "Sheet S/E": [r["sheet_se"] or "—" for r in filtered],
            "Code": [r["code"] for r in filtered],
            "Title": [r["title"] for r in filtered],
        }
    )
    df_key = f"archive_df_{_archive_wkey(sel)}"
    sel_supported = _dataframe_row_selection_supported()

    if sel_supported:
        event = st.dataframe(
            disp,
            column_config={
                "Title": st.column_config.TextColumn("Title", width="large"),
                "#": st.column_config.NumberColumn("#", format="%d", width="small"),
            },
            use_container_width=True,
            height=360,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row-required",
            key=df_key,
        )
        rows_sel: list[int] = []
        try:
            rows_sel = list(event["selection"]["rows"])  # type: ignore[index]
        except (KeyError, TypeError, AttributeError):
            pass
        picked_idx: Optional[int] = None
        if rows_sel:
            try:
                picked_idx = int(rows_sel[0])
            except (TypeError, ValueError, IndexError):
                picked_idx = None
        st.markdown("**Selected row**")
        if picked_idx is not None and 0 <= picked_idx < len(filtered):
            one = filtered[picked_idx]
            sr1, sr2 = st.columns(2)
            with sr1:
                st.metric("Schedule #", str(one["schedule_num"]))
                st.metric("Code", one["code"] or "—")
            with sr2:
                st.metric("S×E (normalized)", one["se_compact"])
                st.metric("0-based index", str(one["idx0"]))
            st.caption("Normalized **Episode** cell (whitespace collapsed)")
            raw = str(one["raw_cell"])
            st.code(raw if len(raw) <= 800 else raw[:800] + "…", language=None)
        else:
            st.info("Click a row in the table above to see full detail here.")
    else:
        st.dataframe(disp, use_container_width=True, height=360, hide_index=True)
        st.warning(
            "Your Streamlit is too old for **clickable table rows**. Upgrade: "
            "`pip install -U \"streamlit>=1.35\"`, then restart the app."
        )
        ix = st.selectbox(
            "Pick a row (fallback)",
            list(range(len(filtered))),
            format_func=lambda i: (
                f"#{filtered[i]['schedule_num']}  {filtered[i]['se_compact']}  {filtered[i]['code']}  —  "
                f"{str(filtered[i]['title'])[:160]}"
            ),
            key=f"archive_jump_{_archive_wkey(sel)}",
        )
        one = filtered[int(ix)]
        st.metric("Schedule #", str(one["schedule_num"]))
        st.metric("S×E", one["se_compact"])
        raw = str(one["raw_cell"])
        st.caption("Normalized **Episode** cell")
        st.code(raw if len(raw) <= 800 else raw[:800] + "…", language=None)


def _month_key(m: date) -> str:
    return f"{m.year:04d}-{m.month:02d}"


def _build_state_path(cfg_path: Path) -> Path:
    return cfg_path.resolve().parent / "schedule_build_state.json"


def _legacy_build_state_path(cfg_path: Path) -> Path:
    return cfg_path.resolve().parent / "playlist_build_state.json"


def _completed_months_from_file(path: Path, config_resolved: str) -> set[str]:
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set()
    if data.get("config_resolved") != config_resolved:
        return set()
    cm = data.get("completed_months")
    if not isinstance(cm, list):
        return set()
    return {str(x) for x in cm if x}


def _load_completed_months(cfg_path: Path) -> set[str]:
    resolved = str(cfg_path.resolve())
    return _completed_months_from_file(_build_state_path(cfg_path), resolved) | _completed_months_from_file(
        _legacy_build_state_path(cfg_path), resolved
    )


def _record_completed_month(cfg_path: Path, month_start: date) -> None:
    p = _build_state_path(cfg_path)
    resolved = str(cfg_path.resolve())
    prev = _load_completed_months(cfg_path)
    prev.add(_month_key(month_start))
    out = {
        "version": 1,
        "config_resolved": resolved,
        "completed_months": sorted(prev),
    }
    p.write_text(json.dumps(out, indent=2), encoding="utf-8")


def _parse_sequence_start(raw: Optional[str]) -> Optional[date]:
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()
    try:
        d = date.fromisoformat(s[:10])
    except ValueError:
        return None
    return date(d.year, d.month, 1)


def _pipeline_months(months_all: list[date], build_sequence_start: Optional[str]) -> list[date]:
    """Months in the in-app unlock chain (subset of ``months_all``), in calendar order."""
    if not months_all:
        return []
    start = _parse_sequence_start(build_sequence_start)
    if start is None:
        return list(months_all)
    sm = (start.year, start.month)
    return [m for m in months_all if (m.year, m.month) >= sm]


def _unlocked_months(pipeline: list[date], completed: set[str]) -> list[date]:
    """Sequential unlock: first month always; each next month appears after the previous is marked complete."""
    if not pipeline:
        return []
    out: list[date] = []
    for i, m in enumerate(pipeline):
        if i == 0:
            out.append(m)
            continue
        prev = pipeline[i - 1]
        if _month_key(prev) in completed:
            out.append(m)
        else:
            break
    return out


def _sorted_weeks(weeks: list) -> list:
    return sorted(weeks, key=lambda w: parse_monday(w.monday))


def _weeks_for_unlocked_months(weeks: list, unlocked_months: list[date]) -> list:
    mm = {(d.year, d.month) for d in unlocked_months}
    return [w for w in _sorted_weeks(weeks) if (parse_monday(w.monday).year, parse_monday(w.monday).month) in mm]


def _effective_weeks_from_start(all_weeks: list, start_on: date, count: int) -> list:
    if not all_weeks:
        return []
    sorted_weeks = _sorted_weeks(all_weeks)
    start_idx = 0
    for i, w in enumerate(sorted_weeks):
        mon = parse_monday(w.monday)
        if mon <= start_on < mon + timedelta(days=7):
            start_idx = i
            break
        if mon >= start_on:
            start_idx = i
            break
    tail = sorted_weeks[start_idx:]
    return tail[: max(1, int(count))]


def _format_duration_minutes(minutes: int) -> str:
    h, m = divmod(int(minutes), 60)
    if h and m:
        return f"{h}h {m}m"
    if h:
        return f"{h}h"
    return f"{m}m"


def _schedule_template_slots(weeks: list) -> tuple[list[dict[str, Any]], list[str]]:
    slots: list[dict[str, Any]] = []
    warnings: list[str] = []
    for w in _sorted_weeks(weeks):
        mon = parse_monday(w.monday)
        try:
            grid = load_grid_sheet(w.grids_file, w.sheet_name)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"Could not load grid `{w.sheet_name}` in `{Path(w.grids_file).name}`: {e}")
            continue
        dates = day_dates(mon)
        for day_idx in range(7):
            col = [grid[r][day_idx] for r in range(48)]
            try:
                segs = segments_for_day(col)
            except ValueError as e:
                warnings.append(f"Bad grid column in `{w.sheet_name}` (day {day_idx}): {e}")
                continue
            for seg in segs:
                minutes = int(seg.end_slot - seg.start_slot) * 30
                d = dates[day_idx]
                st = slot_label(seg.start_slot)
                fin = slot_label(seg.end_slot % 48)
                show_text = str(seg.cell_text).strip()
                slot_id = f"{d.isoformat()}|{st}|{day_idx}|{seg.start_slot}|{w.monday}"
                slots.append(
                    {
                        "slot_id": slot_id,
                        "date": d,
                        "date_iso": d.isoformat(),
                        "week_monday": w.monday,
                        "day_index": day_idx,
                        "start_slot": int(seg.start_slot),
                        "end_slot": int(seg.end_slot),
                        "start": st,
                        "finish": fin,
                        "duration_minutes": minutes,
                        "duration_label": _format_duration_minutes(minutes),
                        "show": show_text,
                    }
                )
    slots.sort(key=lambda r: (r["date_iso"], r["start_slot"], r["show"].casefold()))
    return slots, warnings


def _slot_picker_label(row: dict[str, Any]) -> str:
    return (
        f"{row['date_iso']} {row['start']}-{row['finish']} ({row['duration_label']}) · "
        f"{row['show']} · week {row['week_monday']}"
    )


def _monday_for_calendar_date(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _map_output_grid_tabs_by_monday(grids_path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        import openpyxl

        wb = openpyxl.load_workbook(grids_path, read_only=True)
        try:
            for sn in wb.sheetnames:
                md = parse_sheet_tab_monday(sn)
                if md is not None:
                    out[md.isoformat()] = sn
        finally:
            wb.close()
    except Exception:  # noqa: BLE001
        return out
    return out


def _apply_output_grid_slot_replacements(
    grids_path: Path,
    slot_rows: list[dict[str, Any]],
    new_display: str,
) -> list[str]:
    msgs: list[str] = []
    if not grids_path.is_file():
        return [f"OTO grids update skipped: output file missing `{grids_path}`."]
    tab_by_monday = _map_output_grid_tabs_by_monday(grids_path)
    if not tab_by_monday:
        return [f"OTO grids update skipped: could not map week tabs in `{grids_path.name}`."]
    try:
        import openpyxl

        wb = openpyxl.load_workbook(grids_path, read_only=False, data_only=False)
    except OSError as e:
        return [f"OTO grids update skipped: could not open `{grids_path}` ({e})."]
    changed = 0
    try:
        for r in slot_rows:
            d = r["date"]
            mon_key = _monday_for_calendar_date(d).isoformat()
            tab = tab_by_monday.get(mon_key)
            if not tab or tab not in wb.sheetnames:
                continue
            ws = wb[tab]
            col = 2 + int(r["day_index"])
            for slot in range(int(r["start_slot"]), int(r["end_slot"])):
                ws.cell(row=5 + slot, column=col, value=new_display)
                changed += 1
        wb.save(grids_path)
    finally:
        wb.close()
    msgs.append(f"OTO grids update: replaced {changed} output cell(s) with `{new_display}` in `{grids_path.name}`.")
    return msgs


def _list_xlsx_sheet_names(path: Path) -> list[str]:
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True)
    try:
        return list(wb.sheetnames)
    finally:
        wb.close()


def _list_binge_data_sheets(path: Path) -> list[str]:
    return [s for s in _list_xlsx_sheet_names(path) if s != "BINGE notes"]


def _list_grids_data_sheets(path: Path) -> list[str]:
    return [s for s in _list_xlsx_sheet_names(path) if s != "BINGE notes"]


def _find_binge_column_ci(df: pd.DataFrame, name: str) -> Optional[str]:
    """Return actual column name whose stripped upper case equals ``name``."""
    nu = name.strip().upper()
    for c in df.columns:
        if str(c).strip().upper() == nu:
            return str(c)
    return None


def _schedule_anchor_dict_from_binge_row(df: pd.DataFrame, idx: int) -> Optional[dict[str, Any]]:
    """DATE + START TIME from a BINGE row for single-slot grid edits."""
    dc = _find_binge_column_ci(df, "DATE")
    sc = _find_binge_column_ci(df, "START TIME")
    if not dc or not sc:
        return None
    return {"date": df.iloc[int(idx)][dc], "start": df.iloc[int(idx)][sc]}


def _binge_row_swap_summary(df: pd.DataFrame, idx: int) -> str:
    """One-line label for fallback row picker."""
    r = df.iloc[int(idx)]

    def _cell(col: Optional[str]) -> str:
        if not col or col not in r.index:
            return "?"
        v = r[col]
        if pd.isna(v):
            return "?"
        s = str(v).strip()
        return s if s else "?"

    sc = _find_binge_column_ci(df, "SHOW")
    stc = _find_binge_column_ci(df, "START TIME")
    ec = _find_binge_column_ci(df, "EPISODE")
    return f"Row {idx + 1}: {_cell(sc)} · {_cell(ec)} · {_cell(stc)}"


def _display_name_for_archive_pick(cfg, sel: str) -> str:
    tab = parse_workbook_tab_option(sel)
    if tab is not None:
        return synthetic_series_for_tab(tab).display_name
    return cfg.shows[sel].display_name


def _showdef_for_archive_pick(cfg, sel: str) -> Optional[ShowDef]:
    tab = parse_workbook_tab_option(sel)
    if tab is not None:
        return synthetic_series_for_tab(tab)
    return cfg.shows.get(sel)


def _episode_rows_for_archive_pick(cfg, sel: str, nikki_path: Path) -> list[dict[str, Any]]:
    sd = _showdef_for_archive_pick(cfg, sel)
    if sd is None or sd.kind != "series" or not sd.nikki_sheet or not nikki_path.is_file():
        return []
    style = sd.nikki_style or nikki.default_style_for_sheet(sd.nikki_sheet)
    hdrs = nikki.effective_column_headers(sd, style=style)
    try:
        return _archive_sheet_episodes(
            str(nikki_path.resolve()),
            _nikki_mtime(nikki_path),
            sd.nikki_sheet,
            style,
            sd.prefix or "",
            sd.nikki_row_filter,
            json.dumps(asdict(hdrs), sort_keys=True),
        )
    except Exception:
        return []


def _episode_num_text(ep: dict[str, Any]) -> str:
    for k in ("sheet_se", "se_compact", "ep_in_season", "code"):
        v = ep.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s and s != "—":
            return s
    return ""


def _slot_source_show_key(cfg, slot_show_text: str) -> Optional[str]:
    key, sd = resolve_show(str(slot_show_text or ""), cfg.shows)
    if sd is None or key == "literal":
        return None
    return key


def _semantic_group_for_show(cfg, show_key: str) -> str:
    sd = cfg.shows.get(show_key)
    if sd is None:
        return ""
    return str(getattr(sd, "semantic_group", None) or "").strip().lower()


def _semantic_candidates(cfg, *, group: str, kind: str, exclude_keys: set[str]) -> list[str]:
    out: list[str] = []
    for k, sd in cfg.shows.items():
        if sd.kind != kind:
            continue
        if k in exclude_keys:
            continue
        g = str(getattr(sd, "semantic_group", None) or "").strip().lower()
        if group and g != group:
            continue
        out.append(k)
    out.sort(key=lambda k: cfg.shows[k].display_name.casefold())
    return out


def _grids_preview_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Show blank cells in the GRIDS preview instead of ``None`` / ``nan`` text."""

    def _cell(v: Any) -> Any:
        if v is None:
            return ""
        try:
            if pd.isna(v):
                return ""
        except (TypeError, ValueError):
            pass
        if isinstance(v, str) and v.strip().lower() in ("none", "nan"):
            return ""
        return v

    dfc = df.copy()
    if hasattr(dfc, "map"):
        return dfc.map(_cell)
    return dfc.applymap(_cell)  # type: ignore[attr-defined]


def _render_binge_grids_preview(*, key_prefix: str, show_swap: bool) -> None:
    """In-page tables from the last generated BINGE / BINGE GRIDS in session (optional swap → archive)."""
    if "binge_path" not in st.session_state or "grids_path" not in st.session_state:
        return
    bp = Path(st.session_state["binge_path"])
    gp = Path(st.session_state["grids_path"])
    if not bp.is_file() or not gp.is_file():
        st.warning("BINGE or BINGE GRIDS file is missing on disk for this session.")
        return

    binge_sheets = _list_binge_data_sheets(bp)
    grid_sheets = _list_grids_data_sheets(gp)
    if not binge_sheets:
        st.warning("No data sheets found in the BINGE workbook (excluding notes).")
        return

    st.markdown("##### Preview in app")
    st.caption("Same files as the downloads — pick a week tab for each workbook.")

    c1, c2 = st.columns(2)
    with c1:
        bs = st.selectbox(
            "BINGE week tab",
            binge_sheets,
            key=f"{key_prefix}_preview_binge_sheet",
        )
    with c2:
        gs = st.selectbox(
            "BINGE GRIDS week tab",
            grid_sheets if grid_sheets else ["(no sheets)"],
            key=f"{key_prefix}_preview_grids_sheet",
        )

    try:
        binge_df = pd.read_excel(bp, sheet_name=bs)
        binge_df = normalize_binge_df_columns(binge_df)
    except Exception as e:
        st.error(f"Could not read BINGE sheet `{bs}`: {e}")
        binge_df = None

    if binge_df is not None:
        st.markdown("###### BINGE")
        show_col = _find_binge_column_ci(binge_df, "SHOW")
        picked_row_idx: Optional[int] = None

        if show_swap and show_col and len(binge_df) > 0:
            sel_supported = _dataframe_row_selection_supported()
            df_key = f"{key_prefix}_binge_swap_df"
            if sel_supported:
                event = st.dataframe(
                    binge_df,
                    use_container_width=True,
                    height=340,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    key=df_key,
                )
                rows_sel: list[int] = []
                try:
                    rows_sel = list(event["selection"]["rows"])  # type: ignore[index]
                except (KeyError, TypeError, AttributeError):
                    pass
                if rows_sel:
                    try:
                        picked_row_idx = int(rows_sel[0])
                    except (TypeError, ValueError, IndexError):
                        picked_row_idx = None
                if picked_row_idx is not None and not (0 <= picked_row_idx < len(binge_df)):
                    picked_row_idx = None
            else:
                st.dataframe(binge_df, use_container_width=True, height=340, hide_index=True)
                st.warning(
                    "Upgrade Streamlit for row selection in the table: "
                    "`pip install -U \"streamlit>=1.35\"`. Using row list instead."
                )
                picked_row_idx = int(
                    st.selectbox(
                        "Row to swap",
                        list(range(len(binge_df))),
                        format_func=lambda i: _binge_row_swap_summary(binge_df, int(i)),
                        key=f"{key_prefix}_binge_row_fallback",
                    )
                )

            st.markdown("###### Change a show")
            st.info(
                "**After the BINGE build:** select the **row** you’re replacing, then **Swap for…** and pick **whatever show** "
                "you want from the archive. **Time and day stay the same** — only the program in that slot changes in your **grids** "
                "(and the setup file if the show is new). Run **Create BINGE files** again on **Build schedule** so the spreadsheet matches."
            )
            st.caption("One row → **Swap for… → View content archive** → confirm.")
            if picked_row_idx is not None:
                sv = binge_df.iloc[picked_row_idx][show_col]
                show_val = str(sv).strip() if pd.notna(sv) else ""
                st.caption(f"**Selected row {picked_row_idx + 1} · SHOW:** {show_val or '—'}")
            else:
                st.caption("**No row selected yet** — click a row in the table above.")

            if st.button(
                "Swap for… → View content archive",
                type="secondary",
                use_container_width=True,
                key=f"{key_prefix}_swap_open_archive",
            ):
                if picked_row_idx is None:
                    st.warning("Select exactly one row in the BINGE table first.")
                else:
                    sv = binge_df.iloc[picked_row_idx][show_col]
                    show_val = str(sv).strip() if pd.notna(sv) else ""
                    if not show_val:
                        st.warning("That row has no SHOW value.")
                    else:
                        anchor_dict = _schedule_anchor_dict_from_binge_row(binge_df, picked_row_idx)
                        if anchor_dict is None:
                            st.warning(
                                "This BINGE sheet needs **DATE** and **START TIME** columns so we only edit "
                                "**that** clock slot in the grids (not every week)."
                            )
                        else:
                            st.session_state["swap_context"] = {
                                "old_show_labels": [show_val],
                                "binge_sheet": bs,
                                "binge_row": picked_row_idx + 1,
                                "schedule_anchor": anchor_dict,
                            }
                            st.session_state[_MAIN_NAV_PENDING_KEY] = _NAV_ARCHIVE
                            st.rerun()
        else:
            st.dataframe(binge_df, use_container_width=True, height=340, hide_index=True)
            if show_swap and not show_col:
                st.warning("This BINGE sheet has no **SHOW** column — use another tab or rebuild.")
            elif show_swap and len(binge_df) == 0:
                st.info("This tab has no rows.")

    if grid_sheets and gs != "(no sheets)":
        try:
            grids_df = pd.read_excel(gp, sheet_name=gs, header=None)
        except Exception as e:
            st.error(f"Could not read GRIDS sheet `{gs}`: {e}")
        else:
            st.markdown("###### BINGE GRIDS")
            st.caption("Full sheet layout; program cells are typically rows 5–52, columns B–H (Mon–Sun).")
            max_r = min(len(grids_df), 52)
            st.dataframe(
                _grids_preview_dataframe(grids_df.iloc[:max_r]),
                use_container_width=True,
                height=340,
                hide_index=True,
            )


def _render_content_archive(cfg, cfg_path: Path, nikki_path: Path) -> None:
    swap_ctx = st.session_state.get("swap_context")
    if swap_ctx:
        olds = swap_ctx.get("old_show_labels") or []
        tab_hint = swap_ctx.get("binge_sheet")
        row_hint = swap_ctx.get("binge_row")
        ctx_bits: list[str] = []
        if tab_hint:
            ctx_bits.append(f"tab `{tab_hint}`")
        if row_hint:
            ctx_bits.append(f"row **{row_hint}**")
        ctx_suffix = f" ({', '.join(ctx_bits)})" if ctx_bits else ""
        st.info(
            f"**Swap:** Under **Pick a show**, choose the program you want in that **same time slot**, then "
            f"**Use selected show as replacement**. "
            f"Current label: **{', '.join(olds)}**{ctx_suffix}."
        )

    yaml_keys = sorted(cfg.shows.keys(), key=lambda k: cfg.shows[k].display_name.lower())
    extra_tab_names: list[str] = []
    if nikki_path.is_file():
        tabs = _nikki_workbook_sheet_names(str(nikki_path.resolve()), _nikki_mtime(nikki_path))
        extra_tab_names = workbook_tabs_not_in_yaml(cfg, tabs)
    extra_opts = [workbook_tab_option(t) for t in extra_tab_names]

    option_keys = yaml_keys + extra_opts

    if not option_keys:
        st.info("No shows to list from this setup.")
        return

    def _archive_option_label(opt: str) -> str:
        tab = parse_workbook_tab_option(opt)
        if tab is not None:
            return f"{tab} _(not on schedule)_"
        return cfg.shows[opt].display_name

    sel = st.selectbox(
        "Pick a show",
        option_keys,
        format_func=_archive_option_label,
        key="archive_show_pick",
    )
    if swap_ctx:
        if st.button(
            "Use selected show as replacement",
            type="primary",
            use_container_width=True,
            key="archive_swap_confirm",
        ):
            pick = st.session_state.get("archive_show_pick")
            if not pick:
                st.warning("Pick a show in the list first.")
            else:
                ok, swap_msgs = apply_show_swap(
                    cfg_path,
                    list(swap_ctx.get("old_show_labels") or []),
                    pick,
                    schedule_anchor=swap_ctx.get("schedule_anchor"),
                )
                if ok:
                    combined_msgs = list(swap_msgs)
                    auto_ok = False
                    anchor = swap_ctx.get("schedule_anchor")
                    noop_same_show = "no grid change" in " ".join(swap_msgs).casefold()
                    if anchor and not noop_same_show:
                        r_ok, r_msgs, paths = _regenerate_binge_for_month(cfg_path, anchor)
                        combined_msgs.extend(r_msgs)
                        if r_ok and paths:
                            bp, gp, od = paths
                            st.session_state["binge_path"] = bp
                            st.session_state["grids_path"] = gp
                            st.session_state["out_dir"] = od
                            auto_ok = True
                    st.session_state["swap_result"] = {
                        "old_show_labels": list(swap_ctx.get("old_show_labels") or []),
                        "archive_pick": pick,
                        "new_display": _display_name_for_archive_pick(cfg, pick),
                        "messages": combined_msgs,
                        "auto_export_ok": auto_ok,
                    }
                    st.session_state.pop("swap_context", None)
                    st.session_state[_MAIN_NAV_PENDING_KEY] = _NAV_EDIT_SCHEDULE
                    st.rerun()
                else:
                    for m in swap_msgs:
                        st.error(m)
        if st.button(
            "Cancel swap",
            use_container_width=True,
            key="archive_swap_cancel",
        ):
            st.session_state.pop("swap_context", None)
            st.rerun()

    tab_only = parse_workbook_tab_option(sel)
    if tab_only is not None:
        st.caption(f"Excel tab `{tab_only}` — **not on schedule**")
    else:
        st.caption(f"Schedule entry `{sel}`")

    browse_only = tab_only is not None
    sd = synthetic_series_for_tab(tab_only) if browse_only else cfg.shows[sel]
    with _archive_detail_panel():
        st.markdown(f"## {sd.display_name}")
        if browse_only:
            st.caption(
                "Browse only — add this show to your **setup file** on the schedule (with the same **`nikki_sheet`** "
                "name as this tab) so **Create BINGE files** can use it."
            )
        else:
            st.caption(f"Setup key `{sel}`")

        if sd.kind == "series":
            style = sd.nikki_style or (
                nikki.default_style_for_sheet(sd.nikki_sheet) if sd.nikki_sheet else "generic"
            )
            hdrs = nikki.effective_column_headers(sd, style=style)
            sheet_ok = _nikki_sheet_exists(nikki_path, sd.nikki_sheet)

            _render_archive_episode_browser(
                sel,
                sd,
                nikki_path,
                style=style,
                hdrs=hdrs,
                sheet_ok=sheet_ok,
                browse_only=browse_only,
            )

            with st.expander("Source & technical details", expanded=False):
                st.caption(
                    f"Parser **`{style}`** · start index **{sd.start_episode_index}** · prefix **{sd.prefix or '—'}**"
                )
                if sd.nikki_row_filter:
                    st.caption(f"Row filter: `{sd.nikki_row_filter}`")
                st.markdown("**Spreadsheet tab**")
                st.code(sd.nikki_sheet or "(none)", language=None)
                if sheet_ok is True:
                    st.success("Tab name matches your spreadsheet file.")
                elif sheet_ok is False:
                    st.error("Tab not found — compare with the exact name in Excel.")
                elif nikki_path.is_file():
                    st.warning("Could not read the spreadsheet file.")
                else:
                    st.warning("Spreadsheet path missing in setup.")
                if nikki_path.is_file():
                    if st.button(
                        "Open folder",
                        key=f"archive_open_{_archive_wkey(sel)}",
                        type="secondary",
                        use_container_width=True,
                    ):
                        err = _open_folder(nikki_path.parent)
                        if err:
                            if "download buttons" in err:
                                st.info(err)
                            else:
                                st.error(err)
                with st.expander("Column headers (advanced)", expanded=False):
                    if sd.nikki_columns is not None:
                        st.json({k: v for k, v in asdict(sd.nikki_columns).items() if v is not None})
                    else:
                        st.json({k: v for k, v in asdict(hdrs).items() if v is not None})
                with st.expander(
                    "Row rules (advanced)",
                    expanded=sd.nikki_row_filter == nikki.ROW_FILTER_GREEN_EPISODE_CELL,
                ):
                    if sd.nikki_row_filter:
                        st.code(sd.nikki_row_filter, language=None)
                        if sd.nikki_row_filter == nikki.ROW_FILTER_GREEN_EPISODE_CELL:
                            st.caption(
                                "Only green-filled **Episode** cells count for the schedule; **Create BINGE files** "
                                "uses the same rule, and this table matches it."
                            )
                    else:
                        st.caption("Standard rows — no extra filter.")
        else:
            st.markdown("This show is filled from the **weekly grid** only (no episode list).")
            st.metric("Kind", "Literal")
            st.caption(
                "To swap a literal slot, edit the grid Excel for that week or change how the cell text "
                "maps to **display_name** in your setup—use **Build schedule** to confirm names match."
            )


def _render_last_build_outputs(cfg, cfg_path: Path) -> None:
    """Download buttons and details when a build has been run this session."""
    if "binge_path" not in st.session_state or "grids_path" not in st.session_state:
        return
    bp = st.session_state["binge_path"]
    gp = st.session_state["grids_path"]
    od: Path = st.session_state["out_dir"]
    with open(bp, "rb") as f:
        binge_bytes = f.read()
    with open(gp, "rb") as f:
        grids_bytes = f.read()
    st.download_button(
        "BINGE.xlsx",
        binge_bytes,
        file_name="BINGE.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key="dl_binge_shared",
    )
    st.download_button(
        "BINGE GRIDS.xlsx",
        grids_bytes,
        file_name="BINGE GRIDS.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key="dl_grids_shared",
    )
    if st.button("Open output folder", use_container_width=True, key="open_out_shared"):
        err = _open_folder(od)
        if err:
            if "download buttons" in err:
                st.info(err)
            else:
                st.error(err)
        else:
            st.toast(f"Opened: {od}")

    with st.expander("Details", expanded=False):
        st.caption(
            "**BINGE.xlsx** episode code / # / name columns come from your **Nikki** content workbook and the "
            "saved cursor file — not from the grids file. Grids only say *what show* airs *when*. The downloaded "
            "**BINGE GRIDS.xlsx** keeps the same program text as your grids source (titles), not episode lines."
        )
        cur = resolved_cursor_state_path(cfg)
        if cur:
            st.caption(f"Episode order save file: `{cur}`")
        st.caption(f"Wrap when a show runs out: **{cfg.wrap_episodes}**")


def _render_schedule_tab(cfg, cfg_path: Path, nikki_path: Path) -> None:
    sr = st.session_state.get("swap_result")
    if sr:
        if sr.get("auto_export_ok"):
            st.success(
                f"**Grids updated** and **BINGE files regenerated** for that month: **{', '.join(sr['old_show_labels'])}** → "
                f"**{sr['new_display']}** (`{sr['archive_pick']}`). Downloads below are the new **BINGE.xlsx** / **BINGE GRIDS.xlsx**."
            )
        elif sr.get("auto_export_ok") is False:
            st.success(
                f"**Grids updated** for that slot: **{', '.join(sr['old_show_labels'])}** → **{sr['new_display']}** "
                f"(`{sr['archive_pick']}`). **BINGE export** did not run automatically — use **Create BINGE files** on **Build schedule**, "
                "or see *What changed* for details."
            )
        else:
            st.success(
                f"**Grids updated** for that slot: **{', '.join(sr['old_show_labels'])}** → **{sr['new_display']}** "
                f"(`{sr['archive_pick']}`). Run **Create BINGE files** on **Build schedule** to refresh **BINGE.xlsx**."
            )
        msgs = sr.get("messages") or []
        if msgs:
            with st.expander("What changed", expanded=True):
                for m in msgs:
                    st.markdown(f"- {m}")
        if st.button("Dismiss note", key="schedule_dismiss_swap"):
            st.session_state.pop("swap_result", None)
            st.rerun()
        st.divider()

    st.markdown(
        "Your latest export is here and on **Build schedule**. Below: pick the **BINGE row** to replace, then choose the **archive** show — "
        "**clock times stay put**; grids update for the next build."
    )
    completed = _load_completed_months(cfg_path)
    if completed:
        st.caption(
            f"Months marked built in-app: **{', '.join(sorted(completed))}** "
            f"(see `schedule_build_state.json` or legacy `playlist_build_state.json`)."
        )

    if "binge_path" not in st.session_state:
        st.info("Nothing generated yet — go to **Build schedule** and run **Create BINGE files**.")
    else:
        st.markdown("##### Latest files")
        _render_last_build_outputs(cfg, cfg_path)
        _render_binge_grids_preview(key_prefix="schedule", show_swap=True)

    st.divider()
    st.markdown("##### Make changes")
    st.caption(
        "**Edit schedules** in your sources: episodes, order, and show keys live in the setup YAML and Nikki spreadsheet — "
        "not only inside the export files. Edit those, then run **Create BINGE files** again on **Build schedule**."
    )
    setup_abs = cfg_path.resolve()
    st.markdown(f"- **Setup (YAML):** `{setup_abs}`")
    st.markdown(f"- **Content workbook:** `{nikki_path.resolve()}`")
    cur = resolved_cursor_state_path(cfg)
    if cur:
        st.markdown(f"- **Episode cursors:** `{cur}`")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Open setup folder", use_container_width=True, key="pl_open_cfg"):
            err = _open_folder(setup_abs.parent)
            if err and "download buttons" not in err:
                st.error(err)
            elif err:
                st.info(err)
    with c2:
        if nikki_path.is_file() and st.button("Open Nikki folder", use_container_width=True, key="pl_open_nikki"):
            err = _open_folder(nikki_path.parent)
            if err and "download buttons" not in err:
                st.error(err)
            elif err:
                st.info(err)
        elif not nikki_path.is_file():
            st.caption("Nikki path missing — fix **nikki_workbook** in the setup file.")


def _render_build_schedule(cfg, cfg_path: Path, nikki: Path) -> None:
    if not nikki.is_file():
        st.error(
            f"Spreadsheet file not found:\n`{nikki}`\n\n"
            f"Edit **nikki_workbook** in `{cfg_path.name}`."
        )
        return

    if not cfg.weeks:
        st.error("No **weeks** in your setup file — add week lines or use another setup file.")
        return

    months_all = _months_for_build_selector(cfg.weeks)
    if not months_all:
        st.error("No weeks with valid dates in your setup file.")
        return

    pipeline = _pipeline_months(months_all, cfg.build_sequence_start)
    if not pipeline:
        st.error(
            "No months left in the build sequence — check **weeks** dates and **build_sequence_start** in your setup."
        )
        return

    completed = _load_completed_months(cfg_path)
    unlocked = _unlocked_months(pipeline, completed)
    if not unlocked:
        st.error("Could not determine which month to build — check **weeks** in your setup.")
        return

    buildable_weeks = _weeks_for_unlocked_months(cfg.weeks, unlocked)
    if not buildable_weeks:
        st.error("No weeks are currently unlocked to build.")
        return

    prev_m = st.session_state.get("_build_month_iso")
    cur_m = parse_monday(buildable_weeks[0].monday).isoformat()
    if prev_m is not None and prev_m != cur_m:
        for k in ("binge_path", "grids_path", "out_dir"):
            st.session_state.pop(k, None)
    st.session_state["_build_month_iso"] = cur_m

    st.markdown("##### Build options")
    min_day = parse_monday(buildable_weeks[0].monday)
    max_day = parse_monday(buildable_weeks[-1].monday) + timedelta(days=6)
    default_start = parse_monday(buildable_weeks[0].monday)
    start_date = st.date_input(
        "Start date",
        value=default_start,
        min_value=min_day,
        max_value=max_day,
        key="schedule_start_date",
        help="First calendar day to anchor this run (the app uses the containing Monday week).",
    )
    all_from_start = _effective_weeks_from_start(buildable_weeks, start_date, len(buildable_weeks))
    if not all_from_start:
        st.warning("No weeks available from that start date.")
        return
    default_weeks = 1
    week_count = int(
        st.number_input(
            "How many weeks",
            min_value=1,
            max_value=len(all_from_start),
            value=default_weeks,
            step=1,
            key="schedule_week_count",
        )
    )
    selected_weeks = all_from_start[:week_count]
    selected_mondays = [w.monday for w in selected_weeks]
    st.caption(
        f"Selected weeks: **{len(selected_weeks)}** · "
        + ", ".join(f"`{m}`" for m in selected_mondays)
    )
    # Reset change pickers when build window changes, so OTO/mass can never carry stale weeks.
    scope_key = f"{start_date.isoformat()}|{week_count}|{'|'.join(selected_mondays)}"
    if st.session_state.get("_build_scope_key") != scope_key:
        for k in ("build_oto_slot_ids", "build_mass_seed_ids"):
            st.session_state.pop(k, None)
        st.session_state["_build_scope_key"] = scope_key

    template_slots, template_warnings = _schedule_template_slots(selected_weeks)
    for wmsg in template_warnings:
        st.warning(wmsg)
    slot_by_id = {r["slot_id"]: r for r in template_slots}
    slot_ids = [r["slot_id"] for r in template_slots]

    yaml_keys = sorted(cfg.shows.keys(), key=lambda k: cfg.shows[k].display_name.lower())
    extra_tab_names: list[str] = []
    if nikki.is_file():
        tabs = _nikki_workbook_sheet_names(str(nikki.resolve()), _nikki_mtime(nikki))
        extra_tab_names = workbook_tabs_not_in_yaml(cfg, tabs)
    extra_opts = [workbook_tab_option(t) for t in extra_tab_names]
    archive_options = yaml_keys + extra_opts
    current_show_options = sorted({str(r["show"]).strip() for r in template_slots if str(r["show"]).strip()})

    def _archive_pick_label(opt: str) -> str:
        tab = parse_workbook_tab_option(opt)
        if tab is not None:
            return f"{tab} _(not on schedule)_"
        return cfg.shows[opt].display_name

    st.markdown("##### Optional schedule changes")
    st.caption("OTO/mass block pickers are limited to the selected weeks above.")
    use_oto = st.checkbox(
        "Apply OTO (one-time-only) changes for this output",
        key="build_use_oto_changes",
    )
    oto_rows: list[dict[str, Any]] = []
    oto_pick: Optional[str] = None
    oto_source_group = ""
    oto_source_keys: set[str] = set()
    oto_fill_mode = "Auto-populate matching genre show"
    oto_episode_rows: list[dict[str, Any]] = []
    oto_manual_pool: list[dict[str, Any]] = []
    oto_manual_start_idx: Optional[int] = None
    oto_manual_advance = True
    if use_oto:
        if not slot_ids:
            st.warning("No editable schedule blocks found in the selected weeks.")
        else:
            oto_mode = st.radio(
                "OTO mode",
                ("Choose time blocks", "Replace all blocks for one current show"),
                horizontal=True,
                key="build_oto_mode",
            )
            if oto_mode == "Replace all blocks for one current show":
                if not current_show_options:
                    st.warning("No current shows were found in the selected weeks.")
                else:
                    oto_source_show = st.selectbox(
                        "OTO current show to replace",
                        current_show_options,
                        key="build_oto_source_show",
                    )
                    oto_rows = [r for r in template_slots if r["show"] == oto_source_show]
                    st.caption(f"Selected **{len(oto_rows)}** block(s) for `{oto_source_show}`.")
            else:
                oto_ids = st.multiselect(
                    "OTO: choose time blocks",
                    slot_ids,
                    format_func=lambda sid: _slot_picker_label(slot_by_id[sid]),
                    key="build_oto_slot_ids",
                )
                oto_ids = [sid for sid in oto_ids if sid in slot_by_id]
                oto_rows = [slot_by_id[sid] for sid in oto_ids]
            if oto_rows:
                oto_source_keys = {
                    k for k in (_slot_source_show_key(cfg, r["show"]) for r in oto_rows) if k is not None
                }
                src_groups = [g for g in (_semantic_group_for_show(cfg, k) for k in oto_source_keys) if g]
                if src_groups:
                    oto_source_group = sorted(src_groups)[0]
                    st.caption(f"Semantic source group: `{oto_source_group}`")
            mode_opts = [
                "Auto-populate matching genre show",
                "Auto-populate matching genre movie/program",
                "Manual: show > season > episode",
            ]
            oto_fill_mode = st.radio(
                "OTO fill mode",
                mode_opts,
                horizontal=True,
                key="build_oto_fill_mode",
            )
            if oto_fill_mode == "Manual: show > season > episode":
                if archive_options:
                    oto_pick = st.selectbox(
                        "Manual show",
                        archive_options,
                        format_func=_archive_pick_label,
                        key="build_oto_pick",
                    )
                if oto_pick:
                    oto_episode_rows = _episode_rows_for_archive_pick(cfg, oto_pick, nikki)
                    seasons_found = sorted({r["season"] for r in oto_episode_rows if r.get("season") is not None})
                    season_opts: list[str] = ["All seasons"] + [f"Season {s}" for s in seasons_found]
                    if any(r.get("season") is None for r in oto_episode_rows) and seasons_found:
                        season_opts.append("Unnumbered / list order")
                    pick_season = st.selectbox("Season", season_opts, key="build_oto_pick_season")

                    def _manual_season_match(r: dict[str, Any]) -> bool:
                        if pick_season == "All seasons":
                            return True
                        if pick_season.startswith("Season "):
                            return r.get("season") == int(pick_season.replace("Season ", ""))
                        if pick_season == "Unnumbered / list order":
                            return r.get("season") is None
                        return True

                    oto_manual_pool = [r for r in oto_episode_rows if _manual_season_match(r)]
                    if not oto_manual_pool:
                        st.warning("No episodes match the chosen season filter.")
                    else:
                        idx_opts = list(range(len(oto_manual_pool)))
                        oto_manual_start_idx = st.selectbox(
                            "Episode",
                            idx_opts,
                            format_func=lambda i: (
                                f"{oto_manual_pool[i].get('se_compact', '—')}  {oto_manual_pool[i].get('code', '—')}  —  "
                                f"{str(oto_manual_pool[i].get('title', ''))[:140]}"
                            ),
                            key="build_oto_manual_episode_idx",
                        )
                        oto_manual_advance = st.checkbox(
                            "Advance episodes across selected OTO blocks",
                            value=True,
                            key="build_oto_manual_advance",
                        )
            elif oto_fill_mode == "Auto-populate matching genre show":
                auto_show_opts = _semantic_candidates(
                    cfg,
                    group=oto_source_group,
                    kind="series",
                    exclude_keys=oto_source_keys,
                )
                if not auto_show_opts:
                    auto_show_opts = _semantic_candidates(cfg, group="", kind="series", exclude_keys=oto_source_keys)
                if auto_show_opts:
                    oto_pick = st.selectbox(
                        "Matching genre replacement show",
                        auto_show_opts,
                        format_func=lambda k: (
                            f"{cfg.shows[k].display_name} "
                            f"({getattr(cfg.shows[k], 'semantic_group', None) or 'unlabeled'})"
                        ),
                        key="build_oto_pick_auto_show",
                    )
                    oto_episode_rows = _episode_rows_for_archive_pick(cfg, oto_pick, nikki)
                else:
                    st.warning("No related series candidates were found for auto-populate.")
            else:
                auto_movie_opts = _semantic_candidates(
                    cfg,
                    group=oto_source_group,
                    kind="literal",
                    exclude_keys=set(),
                )
                if not auto_movie_opts:
                    auto_movie_opts = _semantic_candidates(cfg, group="", kind="literal", exclude_keys=set())
                if auto_movie_opts:
                    oto_pick = st.selectbox(
                        "Matching genre replacement movie/program",
                        auto_movie_opts,
                        format_func=lambda k: (
                            f"{cfg.shows[k].display_name} "
                            f"({getattr(cfg.shows[k], 'semantic_group', None) or 'unlabeled'})"
                        ),
                        key="build_oto_pick_auto_movie",
                    )
                else:
                    st.warning("No related movie/program candidates were found for auto-populate.")

    use_mass = st.checkbox(
        "Apply mass changes and persist to source schedule files",
        key="build_use_mass_changes",
    )
    mass_rows: list[dict[str, Any]] = []
    mass_pick: Optional[str] = None
    if use_mass:
        if not slot_ids:
            st.warning("No editable schedule blocks found in the selected weeks.")
        else:
            mass_mode = st.radio(
                "Mass mode",
                (
                    "Replace all blocks for one current show (selected weeks)",
                    "Choose seed time blocks + expand pattern",
                ),
                horizontal=False,
                key="build_mass_mode",
            )
            if mass_mode == "Replace all blocks for one current show (selected weeks)":
                if not current_show_options:
                    st.warning("No current shows were found in the selected weeks.")
                else:
                    mass_source_show = st.selectbox(
                        "Mass current show to replace",
                        current_show_options,
                        key="build_mass_source_show",
                    )
                    mass_rows = [r for r in template_slots if r["show"] == mass_source_show]
                    st.caption(f"Selected **{len(mass_rows)}** block(s) for `{mass_source_show}`.")
            else:
                base_ids = st.multiselect(
                    "Mass: choose seed time blocks",
                    slot_ids,
                    format_func=lambda sid: _slot_picker_label(slot_by_id[sid]),
                    key="build_mass_seed_ids",
                )
                base_ids = [sid for sid in base_ids if sid in slot_by_id]
                expand_pattern = st.checkbox(
                    "Expand by pattern (same weekday + start slot + current show)",
                    value=True,
                    key="build_mass_expand_pattern",
                )
                if expand_pattern and base_ids:
                    expanded: set[str] = set()
                    for sid in base_ids:
                        src = slot_by_id.get(sid)
                        if not src:
                            continue
                        for row in template_slots:
                            if (
                                row["day_index"] == src["day_index"]
                                and row["start_slot"] == src["start_slot"]
                                and row["show"].casefold() == src["show"].casefold()
                            ):
                                expanded.add(row["slot_id"])
                    mass_rows = [slot_by_id[sid] for sid in sorted(expanded)]
                else:
                    mass_rows = [slot_by_id[sid] for sid in base_ids if sid in slot_by_id]
            if archive_options:
                mass_pick = st.selectbox(
                    "New show in those time blocks",
                    archive_options,
                    format_func=_archive_pick_label,
                    key="build_mass_pick",
                )
            st.checkbox(
                "I understand mass changes persist to source files.",
                key="build_mass_confirm",
            )

    st.markdown("##### Preview changes")
    st.caption("This run uses the selected start date/week count, plus optional OTO/mass changes below.")
    st.markdown(
        "\n".join(
            [
                f"- Build window: **{start_date.isoformat()}** + **{len(selected_weeks)}** week(s)",
                f"- Weeks: {', '.join(f'`{w.monday}`' for w in selected_weeks)}",
            ]
        )
    )
    if use_oto:
        oto_dur = _format_duration_minutes(sum(int(r["duration_minutes"]) for r in oto_rows)) if oto_rows else "0m"
        oto_name = _display_name_for_archive_pick(cfg, oto_pick) if oto_pick else "—"
        st.markdown(
            f"- OTO: **{len(oto_rows)}** block(s), duration **{oto_dur}**, replacement **{oto_name}**, mode **{oto_fill_mode}**"
        )
    else:
        st.markdown("- OTO: none")
    if use_mass:
        mass_dur = _format_duration_minutes(sum(int(r["duration_minutes"]) for r in mass_rows)) if mass_rows else "0m"
        mass_name = _display_name_for_archive_pick(cfg, mass_pick) if mass_pick else "—"
        st.markdown(
            f"- Mass: **{len(mass_rows)}** block(s), duration **{mass_dur}**, replacement **{mass_name}** (persists)"
        )
    else:
        st.markdown("- Mass: none")

    preflight_issues: list[str] = []
    if use_oto and (not oto_rows or not oto_pick):
        preflight_issues.append("OTO is enabled but block selection and/or replacement show is missing.")
    if use_oto and oto_fill_mode == "Manual: show > season > episode":
        if not oto_manual_pool or oto_manual_start_idx is None:
            preflight_issues.append("OTO manual mode requires a season and episode selection.")
    if use_oto and oto_fill_mode == "Auto-populate matching genre show" and not oto_episode_rows:
        preflight_issues.append("OTO auto-related-show requires a series with parsed episode rows.")
    if use_mass and (not mass_rows or not mass_pick):
        preflight_issues.append("Mass is enabled but block selection and/or replacement show is missing.")
    if use_mass and not st.session_state.get("build_mass_confirm"):
        preflight_issues.append("Mass persistence confirmation is not checked.")
    for issue in preflight_issues:
        st.warning(issue)

    stations_input = st.text_input(
        "Stations (optional)",
        value="",
        placeholder="Comma-separated call letters, e.g. WXYZ, KABC — copies into subfolders under the output",
        key="export_stations_input",
    )

    run = st.button(
        "Create BINGE files",
        type="primary",
        use_container_width=True,
        disabled=bool(preflight_issues),
        help=f"{len(selected_weeks)} selected week tab(s).",
    )

    if run:
        can_run = True
        oto_overrides: list[BingeRowOverride] = []
        oto_display = ""
        if use_oto:
            if not oto_rows:
                st.error("OTO changes are enabled, but no schedule blocks are selected.")
                can_run = False
            elif not oto_pick:
                st.error("OTO changes are enabled, but no replacement show was selected.")
                can_run = False
            else:
                oto_display = _display_name_for_archive_pick(cfg, oto_pick)
                ordered_oto_rows = sorted(oto_rows, key=lambda r: (r["date_iso"], int(r["start_slot"])))
                # Build one replacement payload per selected slot using manual or auto fill mode.
                episode_plan: list[tuple[str, str, str]] = []
                if oto_fill_mode == "Auto-populate matching genre movie/program":
                    episode_plan = [("MOVIE", "MOVIE", oto_display)] * len(ordered_oto_rows)
                else:
                    pool = list(oto_episode_rows)
                    if oto_fill_mode == "Manual: show > season > episode":
                        pool = list(oto_manual_pool)
                    if not pool:
                        st.error("OTO episode pool is empty for this mode.")
                        can_run = False
                    else:
                        pool.sort(key=lambda r: int(r.get("idx0", 0)))
                        if oto_fill_mode == "Manual: show > season > episode" and oto_manual_start_idx is not None:
                            start_idx = int(oto_manual_start_idx)
                            if oto_manual_advance:
                                for i, _ in enumerate(ordered_oto_rows):
                                    ep = pool[(start_idx + i) % len(pool)]
                                    episode_plan.append(
                                        (
                                            str(ep.get("code") or ""),
                                            _episode_num_text(ep),
                                            str(ep.get("title") or ""),
                                        )
                                    )
                            else:
                                ep = pool[start_idx]
                                episode_plan = [
                                    (
                                        str(ep.get("code") or ""),
                                        _episode_num_text(ep),
                                        str(ep.get("title") or ""),
                                    )
                                ] * len(ordered_oto_rows)
                        else:
                            sd_auto = _showdef_for_archive_pick(cfg, oto_pick)
                            start_cursor = int(getattr(sd_auto, "start_episode_index", 0) or 0) if sd_auto else 0
                            start_idx = 0
                            for i, ep in enumerate(pool):
                                if int(ep.get("idx0", i)) >= start_cursor:
                                    start_idx = i
                                    break
                            for i, _ in enumerate(ordered_oto_rows):
                                ep = pool[(start_idx + i) % len(pool)]
                                episode_plan.append(
                                    (
                                        str(ep.get("code") or ""),
                                        _episode_num_text(ep),
                                        str(ep.get("title") or ""),
                                    )
                                )

                for i, row in enumerate(ordered_oto_rows):
                    st_norm = parse_flexible_time(str(row["start"]))
                    fin_norm = parse_flexible_time(str(row["finish"]))
                    ep_code, ep_num, ep_title = episode_plan[i] if i < len(episode_plan) else ("", "", "")
                    if not ep_code and oto_fill_mode != "Auto-populate matching genre movie/program":
                        ep_code = oto_display
                    if not ep_num and oto_fill_mode != "Auto-populate matching genre movie/program":
                        ep_num = ep_code
                    if not ep_title:
                        ep_title = oto_display
                    oto_overrides.append(
                        BingeRowOverride(
                            match_date=row["date"],
                            match_start=st_norm,
                            new_date=row["date"],
                            new_start=st_norm,
                            new_finish=fin_norm,
                            new_episode=ep_code,
                            new_show=oto_display,
                            new_episode_num=ep_num,
                            new_episode_name=ep_title,
                        )
                    )

        if use_mass:
            if not st.session_state.get("build_mass_confirm"):
                st.error("Confirm that mass changes persist to source files before running.")
                can_run = False
            elif not mass_rows:
                st.error("Mass changes are enabled, but no schedule blocks are selected.")
                can_run = False
            elif not mass_pick:
                st.error("Mass changes are enabled, but no replacement show was selected.")
                can_run = False

        if use_mass and can_run and mass_pick:
            mass_total_changed = 0
            mass_messages: list[str] = []
            for row in mass_rows:
                ok, msgs = apply_show_swap(
                    cfg_path,
                    [str(row["show"])],
                    mass_pick,
                    schedule_anchor={"date": row["date"], "start": row["start"]},
                )
                mass_messages.extend(msgs)
                if ok:
                    mass_total_changed += 1
                else:
                    can_run = False
            if mass_total_changed:
                st.success(f"Mass source changes applied to **{mass_total_changed}** selected block(s).")
            for m in mass_messages:
                if "no grid change" in str(m).casefold():
                    st.info(m)
                elif "could not" in str(m).casefold() or "missing" in str(m).casefold():
                    st.warning(m)
                else:
                    st.caption(m)
            if can_run:
                cfg = load_build_config(cfg_path)

        if not can_run:
            return

        try:
            created_grids = ensure_grids_workbooks_for_weeks(selected_weeks)
        except (OSError, ValueError) as e:
            st.error(f"Could not create missing grids workbook(s): {e}")
            created_grids = []
        if created_grids:
            st.success(
                "Created **grids** workbook shell(s). On export, the app copies the **previous month's** "
                "Mon-Sun program into blank weeks when that month is in your setup (e.g. April to May):\n"
                + "\n".join(f"- `{p}`" for p in created_grids)
            )
        missing_grids: list[str] = []
        for w in selected_weeks:
            if not Path(w.grids_file).is_file():
                missing_grids.append(str(Path(w.grids_file)))
        if missing_grids:
            st.error("Grids file not found:\n" + "\n".join(f"- `{p}`" for p in missing_grids))
        else:
            out_dir = Path(tempfile.mkdtemp(prefix="binge_out_"))
            station_kw: Optional[List[str]] = None
            if stations_input.strip():
                station_kw = [x.strip() for x in stations_input.split(",") if x.strip()]
            try:
                with st.spinner("Working…"):
                    binge_path, grids_path, ovw, seeded = export_both(
                        cfg,
                        out_dir,
                        weeks=selected_weeks,
                        binge_row_overrides=oto_overrides or None,
                        binge_ui_notes={
                            "Build window": (
                                f"start={start_date.isoformat()} · weeks={len(selected_weeks)}"
                            ),
                            "OTO changes": (
                                f"{len(oto_overrides)} row override(s)"
                                if oto_overrides
                                else "none"
                            ),
                            "Mass changes": (
                                f"{len(mass_rows)} slot swap(s) persisted to source"
                                if use_mass and mass_rows
                                else "none"
                            ),
                        },
                        export_stations=station_kw,
                    )
            except Exception as e:
                st.error(str(e))
                st.exception(e)
            else:
                if oto_rows and oto_display:
                    for msg in _apply_output_grid_slot_replacements(grids_path, oto_rows, oto_display):
                        st.info(msg)
                st.session_state["binge_path"] = binge_path
                st.session_state["grids_path"] = grids_path
                st.session_state["out_dir"] = out_dir
                for s in seeded:
                    if is_verbose_seed_noise(s):
                        continue
                    if s.startswith("Copied"):
                        st.success(s)
                    elif s.startswith("Archived BINGE reference copy") or s.startswith("Station copy ["):
                        st.success(s)
                    elif any(
                        x in s.lower()
                        for x in ("could not", "cannot load", "missing", "skipping", "no program", "no ``weeks")
                    ):
                        st.warning(s)
                for w in ovw:
                    st.warning(w)
                built_months = sorted(
                    {
                        (parse_monday(w.monday).year, parse_monday(w.monday).month)
                        for w in selected_weeks
                    }
                )
                for y, m in built_months:
                    _record_completed_month(cfg_path, date(y, m, 1))

    if "binge_path" in st.session_state and "grids_path" in st.session_state:
        st.markdown("##### Latest files")
        _render_last_build_outputs(cfg, cfg_path)
        _render_binge_grids_preview(key_prefix="build", show_swap=False)


def main() -> None:
    st.set_page_config(
        page_title="Schedule Builder",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    _mobile_styles()

    page = _render_top_nav()

    st.divider()

    cfg_path = Path(st.session_state["main_setup_yaml"])
    if not cfg_path.is_file():
        st.error(f"Setup file not found: `{cfg_path.resolve()}`")
        st.stop()

    cfg = load_build_config(cfg_path)
    nikki_path = resolved_nikki_workbook_path(cfg)

    if page == _NAV_ARCHIVE:
        st.header(_NAV_ARCHIVE)
        _render_content_archive(cfg, cfg_path, nikki_path)
    elif page == _NAV_EDIT_SCHEDULE:
        st.header(_NAV_EDIT_SCHEDULE)
        _render_schedule_tab(cfg, cfg_path, nikki_path)
    else:
        st.header(_NAV_BUILD)
        _render_build_schedule(cfg, cfg_path, nikki_path)


if __name__ == "__main__":
    main()
