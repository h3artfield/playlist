"""
Playlist Builder — local Streamlit UI to create **BINGE.xlsx** and **BINGE GRIDS.xlsx**.

Run from the project directory:
  streamlit run streamlit_app.py
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import platform
import subprocess
import tempfile
from dataclasses import asdict
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import streamlit as st

from binge_schedule import nikki
from binge_schedule.archive_normalize import normalize_episodes_for_archive
from binge_schedule.config_io import load_build_config
from binge_schedule.models import NikkiColumnHeaders, ShowDef
from binge_schedule.cursor_state import resolved_cursor_state_path
from binge_schedule.export_xlsx import export_both
from binge_schedule.grid import ensure_grids_workbooks_for_weeks, week_overlaps_calendar_month
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
            subprocess.Popen(["xdg-open", str(p)], close_fds=True)
    except OSError as e:
        return str(e)
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
    """Weeks whose Mon-Sun range touches this calendar month (includes e.g. Apr 27 when building May)."""
    y, m = month_start.year, month_start.month
    out = []
    for w in weeks:
        try:
            d = date.fromisoformat(w.monday)
        except ValueError:
            continue
        if week_overlaps_calendar_month(d, y, m):
            out.append(w)
    return sorted(out, key=lambda w: w.monday)


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
        div[data-testid="stSegmentedControl"] {
            width: 100%;
        }
        /* Selected segment: thick border (Build playlist vs Content archive) */
        div[data-testid="stSegmentedControl"] button {
            border-style: solid !important;
            border-radius: 12px !important;
            transition: border-width 0.12s ease, border-color 0.12s ease !important;
        }
        div[data-testid="stSegmentedControl"] button[aria-pressed="false"] {
            border-width: 1px !important;
            border-color: rgba(255, 255, 255, 0.22) !important;
        }
        div[data-testid="stSegmentedControl"] button[aria-pressed="true"] {
            border-width: 3px !important;
            border-color: #ff4b4b !important;
        }
        div[data-testid="stSegmentedControl"] button[aria-checked="true"],
        div[data-testid="stSegmentedControl"] button[aria-selected="true"],
        div[data-testid="stSegmentedControl"] [role="option"][aria-selected="true"] {
            border-width: 3px !important;
            border-color: #ff4b4b !important;
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
            border-color: #ff4b4b !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_top_nav() -> str:
    """Primary section switcher — top bar (replaces sidebar nav). Returns selected page name."""
    st.markdown(
        '<p style="margin:0 0 0.35rem 0;font-size:0.75rem;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;opacity:0.55;">Playlist</p>',
        unsafe_allow_html=True,
    )
    nav_col, setup_col = st.columns([5, 1], vertical_alignment="center")
    with nav_col:
        if hasattr(st, "segmented_control"):
            page = st.segmented_control(
                "Section",
                options=("Build playlist", "Content archive"),
                key="main_nav",
                label_visibility="collapsed",
                width="stretch",
            )
        else:
            page = st.radio(
                "Section",
                ("Build playlist", "Content archive"),
                horizontal=True,
                key="main_nav",
                label_visibility="collapsed",
            )
    with setup_col:
        if "main_setup_yaml" not in st.session_state:
            st.session_state["main_setup_yaml"] = _default_config_display()
        if hasattr(st, "popover"):
            with st.popover("Setup", use_container_width=True):
                st.text_input(
                    "Playlist setup (YAML)",
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
        return "Build playlist"
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
            "Browse only — not on the playlist until you add this tab under **`nikki_sheet`** in your setup. "
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
        f"**{len(rows)}** rows — playlist **#** column matches **Create BINGE files**"
        + (" (when on the playlist)." if not browse_only else " (browse only until added to setup).")
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
            "#": [r["playlist_num"] for r in filtered],
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
                st.metric("Playlist #", str(one["playlist_num"]))
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
                f"#{filtered[i]['playlist_num']}  {filtered[i]['se_compact']}  {filtered[i]['code']}  —  "
                f"{str(filtered[i]['title'])[:160]}"
            ),
            key=f"archive_jump_{_archive_wkey(sel)}",
        )
        one = filtered[int(ix)]
        st.metric("Playlist #", str(one["playlist_num"]))
        st.metric("S×E", one["se_compact"])
        raw = str(one["raw_cell"])
        st.caption("Normalized **Episode** cell")
        st.code(raw if len(raw) <= 800 else raw[:800] + "…", language=None)


def _default_month_index(months: list[date]) -> int:
    """Prefer the next calendar month in the setup file after today (e.g. May while it is still April).

    Episode cursors do not depend on this choice—they come from the last successful build.
    """
    if not months:
        return 0
    today = date.today()
    t = (today.year, today.month)
    for i, first in enumerate(months):
        m = (first.year, first.month)
        if m > t:
            return i
    return len(months) - 1


def _render_content_archive(cfg, cfg_path: Path, nikki_path: Path) -> None:
    st.markdown(
        "**Content archive:** shows **on your April playlist** (from your setup file) are listed first, then **every "
        "other Excel tab** except **`movies`**. **NEW SHOWS** is read as a flat catalog (`Artist — Sort Title`). "
        "**Create BINGE files** only uses shows on the playlist; extra tabs are here so you can review them before "
        "you add them."
    )

    filter_kind = st.radio(
        "Filter",
        ("All", "Series", "Literals"),
        horizontal=False,
        key="archive_filter",
    )

    def include_yaml(key: str) -> bool:
        sd = cfg.shows[key]
        if filter_kind == "All":
            return True
        if filter_kind == "Series":
            return sd.kind == "series"
        return sd.kind == "literal"

    yaml_keys = sorted(
        [k for k in cfg.shows if include_yaml(k)],
        key=lambda k: cfg.shows[k].display_name.lower(),
    )
    extra_tab_names: list[str] = []
    if nikki_path.is_file():
        tabs = _nikki_workbook_sheet_names(str(nikki_path.resolve()), _nikki_mtime(nikki_path))
        extra_tab_names = workbook_tabs_not_in_yaml(cfg, tabs)
    extra_opts = [workbook_tab_option(t) for t in extra_tab_names]

    if filter_kind == "Literals":
        option_keys = yaml_keys
    else:
        option_keys = yaml_keys + extra_opts

    if not option_keys:
        st.info("No shows match this filter.")
        return

    def _archive_option_label(opt: str) -> str:
        tab = parse_workbook_tab_option(opt)
        if tab is not None:
            return f"{tab} _(not in playlist)_"
        return cfg.shows[opt].display_name

    st.markdown("##### Shows & Excel tabs")
    st.caption(
        f"**{len(yaml_keys)}** on your playlist (from the setup file)"
        + (
            f" · **{len(extra_opts)}** more Excel tabs (everything except **`movies`** and tabs already on the playlist)."
            if extra_opts
            else " · every Excel tab is already on the playlist (except **`movies`**)."
        )
    )
    if nikki_path.is_file():
        tabs = _nikki_workbook_sheet_names(str(nikki_path.resolve()), _nikki_mtime(nikki_path))
        st.caption(f"Workbook: **{len(tabs)}** sheets. Audit: `docs/NIKKI_WORKBOOK_TAB_AUDIT.md`.")
    else:
        st.caption("Content workbook path is missing or not a file.")
    sel = st.selectbox(
        "Pick a show",
        option_keys,
        format_func=_archive_option_label,
        label_visibility="collapsed",
        key="archive_show_pick",
    )
    tab_only = parse_workbook_tab_option(sel)
    if tab_only is not None:
        st.caption(f"Excel tab `{tab_only}` — **not in playlist**")
    else:
        st.caption(f"Playlist entry `{sel}`")

    browse_only = tab_only is not None
    sd = synthetic_series_for_tab(tab_only) if browse_only else cfg.shows[sel]
    with _archive_detail_panel():
        st.markdown(f"## {sd.display_name}")
        if browse_only:
            st.caption(
                "Browse only — add this show to your **setup file** on the playlist (with the same **`nikki_sheet`** "
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
                                "Only green-filled **Episode** cells count for the playlist; **Create BINGE files** "
                                "uses the same rule, and this table matches it."
                            )
                    else:
                        st.caption("Standard rows — no extra filter.")
        else:
            st.markdown("This show is filled from the **weekly grid** only (no episode list).")
            st.metric("Kind", "Literal")
            st.caption(
                "To swap a literal slot, edit the grid Excel for that week or change how the cell text "
                "maps to **display_name** in your setup—use **Build playlist** to confirm names match."
            )


def _render_build_playlist(cfg, cfg_path: Path, nikki: Path) -> None:
    if not nikki.is_file():
        st.error(
            f"Spreadsheet file not found:\n`{nikki}`\n\n"
            f"Edit **nikki_workbook** in `{cfg_path.name}`."
        )
        return

    if not cfg.weeks:
        st.error("No **weeks** in your setup file — add week lines or use another setup file.")
        return

    months = _months_for_build_selector(cfg.weeks)
    if not months:
        st.error("No weeks with valid dates in your setup file.")
        return

    month_start = st.selectbox(
        "Build this month",
        months,
        index=_default_month_index(months),
        format_func=lambda d: d.strftime("%B %Y"),
        key="playlist_month",
    )
    prev_m = st.session_state.get("_build_month_iso")
    cur_m = month_start.isoformat()
    if prev_m is not None and prev_m != cur_m:
        for k in ("binge_path", "grids_path", "out_dir"):
            st.session_state.pop(k, None)
    st.session_state["_build_month_iso"] = cur_m

    selected_weeks = _weeks_in_month(cfg.weeks, month_start)
    if not selected_weeks:
        st.warning(
            f"No **`weeks:`** entries yet for **{month_start.strftime('%B %Y')}**. "
            "Add one block per Monday (same shape as April: `monday`, `grids_file`, `sheet_name`). "
            "Episode order still comes from your cursor file after April."
        )
        return

    run = st.button(
        "Create BINGE files",
        type="primary",
        use_container_width=True,
        help=f"{len(selected_weeks)} week tab(s) for {month_start.strftime('%B %Y')}.",
    )

    if run:
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
            try:
                with st.spinner("Working…"):
                    binge_path, grids_path, ovw, seeded = export_both(
                        cfg, out_dir, weeks=selected_weeks
                    )
            except Exception as e:
                st.error(str(e))
                st.exception(e)
            else:
                st.session_state["binge_path"] = binge_path
                st.session_state["grids_path"] = grids_path
                st.session_state["out_dir"] = out_dir
                for s in seeded:
                    if s.startswith("Copied"):
                        st.success(s)
                    elif any(
                        x in s.lower()
                        for x in ("could not", "cannot load", "missing", "skipping", "no program", "no ``weeks")
                    ):
                        st.warning(s)
                for w in ovw:
                    st.warning(w)

    if "binge_path" in st.session_state and "grids_path" in st.session_state:
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
        )
        st.download_button(
            "BINGE GRIDS.xlsx",
            grids_bytes,
            file_name="BINGE GRIDS.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        if st.button("Open folder", use_container_width=True):
            err = _open_folder(od)
            if err:
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


def main() -> None:
    st.set_page_config(
        page_title="Playlist Builder",
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
    nikki_path = Path(cfg.nikki_workbook)

    if page == "Content archive":
        st.header("Content archive")
        _render_content_archive(cfg, cfg_path, nikki_path)
    else:
        st.header("Build playlist")
        _render_build_playlist(cfg, cfg_path, nikki_path)


if __name__ == "__main__":
    main()
