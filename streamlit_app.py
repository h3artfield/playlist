"""
Local UI: upload **BINGE.xlsx** → answer Q&A → generate **BINGE GRIDS.xlsx**.

Run from the project directory:
  streamlit run streamlit_app.py
"""

from __future__ import annotations

import platform
import subprocess
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from binge_schedule.binge_overrides import BingeRowOverride, parse_flexible_time
from binge_schedule.binge_to_grid import read_binge_workbook_sheets
from binge_schedule.config_io import load_build_config
from binge_schedule.export_xlsx import export_grids_from_binge_sheets

# Default for Streamlit Community Cloud / fresh clones (`config/cloud.yaml` has no local paths).
# On your machine, set the sidebar path to `config/april_2026.yaml` if you use Nikki + CLI paths.
_DEFAULT_CONFIG = Path("config/cloud.yaml")


def _open_folder(path: Path) -> str:
    """Open ``path`` in the OS file manager. Returns an error message, or empty string if launch was attempted."""
    p = path.resolve()
    if not p.is_dir():
        return f"Folder not found: {p}"
    system = platform.system()
    try:
        if system == "Windows":
            # ``os.startfile`` often fails under Streamlit / restricted shells; explorer is reliable.
            subprocess.Popen(
                ["explorer.exe", str(p)],
                close_fds=True,
            )
        elif system == "Darwin":
            subprocess.Popen(["open", str(p)], close_fds=True)
        else:
            subprocess.Popen(["xdg-open", str(p)], close_fds=True)
    except OSError as e:
        return str(e)
    return ""


def main() -> None:
    st.set_page_config(page_title="BINGE → Grids", layout="centered")

    with st.sidebar:
        st.markdown("**Settings**")
        cfg_text = st.text_input(
            "Config YAML path",
            value=str(_DEFAULT_CONFIG),
            label_visibility="collapsed",
            help="Gracenote ID & grid styling (file on disk).",
        )
        st.caption(f"Using config: `{cfg_text}`")

    _, main_col, _ = st.columns([0.1, 0.8, 0.1])

    with main_col:
        st.markdown("## BINGE → Grids")
        st.caption("Turn your BINGE list into a formatted **BINGE GRIDS** workbook.")

        uploaded = st.file_uploader(
            "Choose BINGE.xlsx",
            type=["xlsx"],
            help="Must include columns like DATE, START TIME, FINISH TIME, EPISODE, SHOW…",
        )

        if not uploaded:
            st.markdown("---")
            st.info("**Choose a file** above to get started.")
            st.stop()

        upload_key = f"{uploaded.name}:{uploaded.size}"
        if st.session_state.get("_upload_key") != upload_key:
            for k in ("grids_path", "out_dir"):
                st.session_state.pop(k, None)
            st.session_state["_upload_key"] = upload_key

        cfg_path = Path(cfg_text)
        if not cfg_path.is_file():
            st.error(
                f"Config not found: `{cfg_path.resolve()}`. Fix the path in the sidebar."
            )
            st.stop()
        cfg = load_build_config(cfg_path)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp.write(uploaded.getvalue())
            binge_path = Path(tmp.name)

        try:
            all_sheets = read_binge_workbook_sheets(binge_path, skip_notes=True)
        except Exception as e:
            binge_path.unlink(missing_ok=True)
            st.error(f"Could not read this workbook: {e}")
            st.stop()

        if not all_sheets:
            st.error("No data sheets found (empty or only **BINGE notes**).")
            st.stop()

        st.markdown("---")
        st.success(
            f"**File received:** `{uploaded.name}`  \n"
            f"_{len(all_sheets)} sheet(s) · {uploaded.size:,} bytes_"
        )

        with st.expander("Which sheets to include?", expanded=False):
            names = list(all_sheets.keys())
            selected = st.multiselect(
                "Sheets",
                names,
                default=names,
                label_visibility="collapsed",
                help="By default all data sheets are used. Uncheck any to skip.",
            )

        if not selected:
            st.warning("Select at least one sheet in the expander above.")
            st.stop()

        physical_sheets = {n: all_sheets[n] for n in selected}

        st.markdown("### Do you need to make changes?")
        has_changes = st.radio(
            "Schedule changes",
            [
                "No — use the file as uploaded",
                "Yes — I need to replace one or more rows first",
            ],
            index=0,
            horizontal=False,
            label_visibility="collapsed",
        )
        needs_changes = has_changes.startswith("Yes")

        changes_summary = ""
        binge_row_overrides: list[BingeRowOverride] = []
        if needs_changes:
            changes_summary = st.text_area(
                "Briefly, what changed? (saved on the notes sheet)",
                placeholder="e.g. swapped movie on Thursday night…",
                height=88,
            )
            n_ov = st.number_input(
                "How many rows should be replaced?",
                min_value=0,
                max_value=40,
                value=1,
                help="We find each row by **date + start time** in your BINGE file, then overwrite all 7 columns.",
            )
            for i in range(int(n_ov)):
                with st.expander(f"Row {i + 1}", expanded=(int(n_ov) <= 2)):
                    st.caption("Find this row in your uploaded BINGE file")
                    md = st.date_input("Date", key=f"ov{i}_md")
                    ms = st.text_input("Start time", key=f"ov{i}_ms", placeholder="9:30 or 9:30 AM")
                    st.caption("New values (replace entire row)")
                    c3, c4 = st.columns(2)
                    with c3:
                        nd = st.date_input("New date", key=f"ov{i}_nd")
                        ns = st.text_input("New start", key=f"ov{i}_ns")
                        nf = st.text_input("New finish", key=f"ov{i}_nf")
                        ne = st.text_input("Episode", key=f"ov{i}_ne")
                    with c4:
                        nshow = st.text_input("Show", key=f"ov{i}_nshow")
                        nen = st.text_input("Episode #", key=f"ov{i}_nen")
                        nn = st.text_input("Episode name", key=f"ov{i}_nn")
                    binge_row_overrides.append(
                        BingeRowOverride(
                            match_date=md,
                            match_start=ms,
                            new_date=nd,
                            new_start=ns,
                            new_finish=nf,
                            new_episode=ne,
                            new_show=nshow,
                            new_episode_num=nen,
                            new_episode_name=nn,
                        )
                    )

        st.markdown("### A few details")
        station = st.text_input("What station?", placeholder="Call letters or name (optional)")
        dst_choice = st.radio(
            "Daylight time this week?",
            [
                "Neither",
                "Forward (spring ahead)",
                "Backward (fall back)",
            ],
            horizontal=True,
        )

        binge_ui_notes = {
            "What station?": station.strip() or "(not specified)",
            "Are there any changes to the schedule?": "Yes" if needs_changes else "No",
            "What are the changes?": (changes_summary.strip() or "(none)")
            if needs_changes
            else "(n/a — using file as uploaded)",
            "Is this week time forward or backward?": dst_choice,
        }

        st.markdown("---")
        run = st.button(
            "Build BINGE GRIDS",
            type="primary",
            use_container_width=True,
            help="Creates BINGE GRIDS.xlsx (week tabs first; Q&A on the **BINGE notes** tab at the end).",
        )

        if run:
            overrides_to_apply = binge_row_overrides if needs_changes else []
            if needs_changes and overrides_to_apply:
                bad: list[str] = []
                for j, o in enumerate(overrides_to_apply, start=1):
                    try:
                        parse_flexible_time(o.match_start)
                        parse_flexible_time(o.new_start)
                        parse_flexible_time(o.new_finish)
                    except ValueError as e:
                        bad.append(f"Row {j}: {e}")
                if bad:
                    st.error("Fix these times:\n" + "\n".join(bad))
                else:
                    _run_grids_export(
                        cfg,
                        physical_sheets,
                        overrides_to_apply,
                        binge_ui_notes,
                    )
            else:
                _run_grids_export(
                    cfg,
                    physical_sheets,
                    None if not overrides_to_apply else overrides_to_apply,
                    binge_ui_notes,
                )

        if "grids_path" in st.session_state:
            gp = st.session_state["grids_path"]
            od = st.session_state["out_dir"]
            st.markdown("---")
            st.success("**Your grids file is ready.**")
            with open(gp, "rb") as f:
                st.download_button(
                    "Download BINGE GRIDS.xlsx",
                    f.read(),
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
            st.caption(f"If the folder did not open, copy this path: `{od}`")


def _run_grids_export(
    cfg,
    physical_sheets: dict[str, pd.DataFrame],
    overrides: list[BingeRowOverride] | None,
    binge_ui_notes: dict[str, str],
) -> None:
    out_dir = Path(tempfile.mkdtemp(prefix="binge_grids_out_"))
    try:
        with st.spinner("Building your grids…"):
            grids_path, ovw = export_grids_from_binge_sheets(
                cfg,
                physical_sheets,
                out_dir,
                binge_row_overrides=overrides,
                binge_ui_notes=binge_ui_notes,
            )
    except Exception as e:
        st.error(str(e))
        st.exception(e)
    else:
        st.session_state["grids_path"] = grids_path
        st.session_state["out_dir"] = out_dir
        for w in ovw:
            st.warning(w)


if __name__ == "__main__":
    main()
