"""Infer **advance vs repeat** from a reference BINGE workbook (canonical April).

Rules are **per series** and **per clock slot** ``(weekday, half-hour slot)``. If the **grid changes** and a
different show occupies that slot, there is **no** carry-over repeat pattern from the previous show—scheduling
for the new show is just **Nikki playlist order** as it airs (``next_episode`` in chronological order). Repeat
edges only apply when the **same** show key appears at both the reference slot and the repeat slot.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal, Optional, Union

import pandas as pd

from binge_schedule.binge_to_grid import (
    _find_col,
    normalize_binge_df_columns,
    parse_binge_date_cell,
    parse_binge_time_cell,
    wall_time_to_slot_start,
)
from binge_schedule.models import BuildConfig, Catalog, Episode
from binge_schedule.show_resolve import resolve_show

# Per show + calendar slot: either consume next Nikki episode, or replay the episode first seen at (wd_ref, slot_ref).
EpisodeAction = Union[Literal["advance"], tuple[Literal["repeat"], int, int]]
EpisodeActionMap = dict[tuple[str, int, int], EpisodeAction]


def build_episode_actions_from_binge_df(df: pd.DataFrame, cfg: BuildConfig) -> EpisodeActionMap:
    """Walk one ISO week of BINGE rows in **chronological** order.

    For each series half-hour, look at ``EPISODE`` code. The **first** time a given code appears that week for
    that show, the slot is an **advance** (new Nikki episode). Any **later** slot with the **same** code is a
    **repeat** of the first slot’s episode (e.g. Tuesday 0:00–3:30 re-airing Monday 20:00–23:30).

    This captures non-consecutive repeats (overnight blocks) as long as the duplicate codes match.
    """
    df = normalize_binge_df_columns(df.copy())
    c_date = _find_col(df, "DATE")
    c_start = _find_col(df, "START TIME")
    c_show = _find_col(df, "SHOW")
    c_ep = _find_col(df, "EPISODE")

    records: list[tuple] = []
    for _, row in df.iterrows():
        try:
            d = parse_binge_date_cell(row[c_date])
            st = parse_binge_time_cell(row[c_start])
        except (ValueError, TypeError):
            continue
        records.append((d, st, row))

    records.sort(key=lambda t: (t[0], t[1]))

    # (show_key, episode_code) -> (wd, slot) of first appearance this week
    first_slot_for_code: dict[tuple[str, str], tuple[int, int]] = {}
    out: EpisodeActionMap = {}

    for d, st, row in records:
        show_cell = str(row[c_show]).strip() if pd.notna(row[c_show]) else ""
        code = str(row[c_ep]).strip() if pd.notna(row[c_ep]) else ""
        if not show_cell or not code:
            continue
        if code.upper() == "MOVIE":
            continue

        key, sd = resolve_show(show_cell, cfg.shows)
        if sd is None or key == "literal" or sd.kind != "series":
            continue

        wd = d.weekday()
        slot = wall_time_to_slot_start(st)
        loc = (wd, slot)
        ck = (key, code)

        if ck not in first_slot_for_code:
            first_slot_for_code[ck] = loc
            out[(key, wd, slot)] = "advance"
        else:
            wd_r, sl_r = first_slot_for_code[ck]
            if (wd, slot) == (wd_r, sl_r):
                continue
            out[(key, wd, slot)] = ("repeat", wd_r, sl_r)

    return out


def merge_episode_action_maps(per_sheet: list[tuple[str, EpisodeActionMap]]) -> EpisodeActionMap:
    """Merge actions from multiple April weeks. Earlier sheet in chronological order wins on duplicate keys."""
    merged: EpisodeActionMap = {}
    for _sheet_name, m in per_sheet:
        for k, v in m.items():
            if k not in merged:
                merged[k] = v
            # On conflict, keep the value already set from an earlier week (silent).
    return merged


def load_reference_episode_actions(
    cfg: BuildConfig,
) -> tuple[Optional[EpisodeActionMap], Optional[str], list[str]]:
    """Load episode actions from ``reference_binge_file``.

    Returns ``(map, file_warning, merge_notes)`` — ``merge_notes`` is always empty (reserved).
    """
    merge_notes: list[str] = []
    if not cfg.reference_binge_file or not str(cfg.reference_binge_file).strip():
        return None, None, merge_notes
    raw = Path(cfg.reference_binge_file.strip())
    if not raw.is_absolute():
        base = cfg.config_path.parent if cfg.config_path else Path.cwd()
        raw = (base / raw).resolve()
    if not raw.is_file():
        return None, (
            f"reference_binge_file not found ({raw}); scheduling uses Nikki advance every slot. "
            f"Fix the path or restore the workbook."
        ), merge_notes

    from binge_schedule.binge_to_grid import read_binge_workbook_sheets

    sheets = read_binge_workbook_sheets(raw)
    if not sheets:
        return None, f"No data sheets in reference BINGE workbook {raw}", merge_notes

    if cfg.reference_binge_all_sheets:
        from binge_schedule.binge_to_grid import infer_monday_from_binge_df

        def _sheet_order(name: str) -> tuple:
            try:
                return (infer_monday_from_binge_df(sheets[name]), name)
            except Exception:
                return (name,)

        ordered_maps: list[tuple[str, EpisodeActionMap]] = []
        for name in sorted(sheets.keys(), key=_sheet_order):
            ordered_maps.append((name, build_episode_actions_from_binge_df(sheets[name], cfg)))
        return merge_episode_action_maps(ordered_maps), None, merge_notes

    want = (cfg.reference_binge_sheet or "").strip()
    if want:
        if want not in sheets:
            names = ", ".join(repr(s) for s in sheets)
            raise ValueError(
                f"reference_binge_sheet {want!r} not in {raw}; available: {names}"
            )
        df = sheets[want]
    else:
        df = next(iter(sheets.values()))
    return build_episode_actions_from_binge_df(df, cfg), None, merge_notes


def resolved_reference_binge_path(cfg: BuildConfig) -> Optional[Path]:
    if not cfg.reference_binge_file or not str(cfg.reference_binge_file).strip():
        return None
    raw = Path(cfg.reference_binge_file.strip())
    if not raw.is_absolute():
        base = cfg.config_path.parent if cfg.config_path else Path.cwd()
        raw = (base / raw).resolve()
    return raw if raw.is_file() else None


def load_reference_week_dataframe(cfg: BuildConfig, monday: date) -> Optional[pd.DataFrame]:
    """Return the reference BINGE rows for the ISO week starting ``monday``, if present in the workbook."""
    path = resolved_reference_binge_path(cfg)
    if path is None:
        return None
    from binge_schedule.binge_to_grid import infer_monday_from_binge_df, read_binge_workbook_sheets, split_binge_df_by_monday

    sheets = read_binge_workbook_sheets(path)
    for name in sorted(sheets.keys(), key=lambda n: (infer_monday_from_binge_df(sheets[n]), n)):
        by_mon = split_binge_df_by_monday(sheets[name])
        if monday in by_mon:
            return by_mon[monday]
    return None


def _episode_index_for_binge_code(eps: list[Episode], raw_code: str) -> Optional[int]:
    """Match a BINGE ``EPISODE`` cell to a Nikki row index (next ``next_episode`` should emit this row)."""
    raw = raw_code.strip().upper().replace(" ", "")
    if not raw:
        return None
    for i, e in enumerate(eps):
        ec = str(e.code).strip().upper()
        if ec == raw:
            return i
        if raw.isdigit() and e.episode_num is not None and int(raw) == int(e.episode_num):
            return i
        if len(raw) >= 3 and ec.endswith(raw[-3:]) and raw[-3:].isdigit():
            if e.episode_num is not None and int(raw[-3:]) == int(e.episode_num):
                return i
    return None


def sync_cursors_from_reference_binge_week(
    cfg: BuildConfig,
    cat: Catalog,
    week_df: pd.DataFrame,
    *,
    monday_label: str,
) -> list[str]:
    """Set ``cat.cursor[show]`` so the first time each series appears this week matches reference ``EPISODE`` codes.

    Walks ``week_df`` in time order; the **first** row for each series show sets that show’s cursor to the Nikki
    index that would emit that code on the next ``next_episode`` call.

    Returned strings are **only** warnings when a reference code has no matching Nikki row (skipped); per-show
    success lines are not emitted.
    """
    notes: list[str] = []
    df = normalize_binge_df_columns(week_df.copy())
    c_date = _find_col(df, "DATE")
    c_start = _find_col(df, "START TIME")
    c_show = _find_col(df, "SHOW")
    c_ep = _find_col(df, "EPISODE")

    records: list[tuple] = []
    for _, row in df.iterrows():
        try:
            d = parse_binge_date_cell(row[c_date])
            st = parse_binge_time_cell(row[c_start])
        except (ValueError, TypeError):
            continue
        records.append((d, st, row))

    records.sort(key=lambda t: (t[0], t[1]))
    seen_show: set[str] = set()

    for _d, _st, row in records:
        show_cell = str(row[c_show]).strip() if pd.notna(row[c_show]) else ""
        code = str(row[c_ep]).strip() if pd.notna(row[c_ep]) else ""
        if not show_cell or not code or code.upper() == "MOVIE":
            continue
        key, sd = resolve_show(show_cell, cfg.shows)
        if sd is None or key == "literal" or sd.kind != "series":
            continue
        if key in seen_show:
            continue
        seen_show.add(key)
        if key not in cat.by_show:
            continue
        eps = cat.by_show[key]
        idx = _episode_index_for_binge_code(eps, code)
        if idx is None:
            notes.append(
                f"{monday_label} sync: no Nikki row for show '{key}' code {code!r} (skipped)."
            )
            continue
        cat.cursor[key] = idx

    return notes


def reconcile_catalog_from_binge_dataframe(cfg: BuildConfig, cat: Catalog, df: pd.DataFrame) -> None:
    """Set ``cat.cursor`` from a finished BINGE dataframe (chronological walk; same-code repeat does not advance)."""
    df = normalize_binge_df_columns(df.copy())
    c_date = _find_col(df, "DATE")
    c_start = _find_col(df, "START TIME")
    c_show = _find_col(df, "SHOW")
    c_ep = _find_col(df, "EPISODE")

    records: list[tuple[date, Any, Any]] = []
    for _, row in df.iterrows():
        try:
            d = parse_binge_date_cell(row[c_date])
            st = parse_binge_time_cell(row[c_start])
        except (ValueError, TypeError):
            continue
        records.append((d, st, row))

    records.sort(key=lambda t: (t[0], t[1]))
    last_code: dict[str, str] = {}

    for _d, _st, row in records:
        show_cell = str(row[c_show]).strip() if pd.notna(row[c_show]) else ""
        code = str(row[c_ep]).strip() if pd.notna(row[c_ep]) else ""
        if not show_cell or not code or code.upper() == "MOVIE":
            continue
        key, sd = resolve_show(show_cell, cfg.shows)
        if sd is None or key == "literal" or sd.kind != "series":
            continue
        if key not in cat.by_show:
            continue
        eps = cat.by_show[key]
        idx = _episode_index_for_binge_code(eps, code)
        if idx is None:
            continue
        if last_code.get(key) == code:
            continue
        cat.cursor[key] = idx + 1
        last_code[key] = code


def merge_literal_reference_binge_days(
    cfg: BuildConfig,
    monday: date,
    generated: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str]]:
    """Replace generated rows before ``reference_binge_literal_copy_before`` with rows from the reference workbook.

    May days (on or after the cutoff date) stay **generated**; earlier calendar days are **copy-pasted** from
    the canonical April BINGE for that ISO week. The returned notes list is always empty (no UI chatter).
    """
    raw = (cfg.reference_binge_literal_copy_before or "").strip()
    if not raw:
        return generated, []
    try:
        cutoff = date.fromisoformat(raw)
    except ValueError:
        return generated, []

    ref = load_reference_week_dataframe(cfg, monday)
    if ref is None:
        return generated, []

    gen = normalize_binge_df_columns(generated.copy())
    ref_df = normalize_binge_df_columns(ref.copy())
    c_date_g = _find_col(gen, "DATE")
    c_date_r = _find_col(ref_df, "DATE")

    def row_d(r: pd.Series, c_col) -> date:
        return parse_binge_date_cell(r[c_col])

    gen_keep = gen[gen.apply(lambda r: row_d(r, c_date_g) >= cutoff, axis=1)]
    ref_take = ref_df[ref_df.apply(lambda r: row_d(r, c_date_r) < cutoff, axis=1)]

    if ref_take.empty:
        return generated, []

    merged = pd.concat([gen_keep, ref_take], ignore_index=True)

    cg = _find_col(merged, "DATE")
    cs = _find_col(merged, "START TIME")

    def sort_dt(r: pd.Series) -> datetime:
        try:
            d = parse_binge_date_cell(r[cg])
            st = parse_binge_time_cell(r[cs])
            return datetime.combine(d, st)
        except Exception:
            return datetime.min

    merged["_dt"] = merged.apply(sort_dt, axis=1)
    merged = merged.sort_values("_dt", kind="mergesort").drop(columns=["_dt"])
    return merged, []
