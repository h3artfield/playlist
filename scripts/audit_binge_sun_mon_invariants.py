#!/usr/bin/env python3
"""
Audit BINGE list workbooks for the overnight invariant:

  On the Monday immediately following a Sunday, for each series block in
  00:00–04:00, the EPISODE codes should match the *last* N rows of that show’s
  Sunday 20:00–24:00 block, where N = number of Monday 00:00–04:00 rows for
  that show (often 8× half-hour = “last 8 episodes”).

Loads every *BINGE*.xlsx under a directory (excluding *GRIDS*), merges all
sheets, aligns by calendar date + clock, and reports matches / mismatches /
missing data.

Usage (from repo root):
  python scripts/audit_binge_sun_mon_invariants.py [path/to/dir_or_file ...]

Default: data/ under the repo root.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from binge_schedule.binge_to_grid import (  # noqa: E402
    _find_col,
    normalize_binge_df_columns,
    parse_binge_date_cell,
    parse_binge_time_cell,
    read_binge_workbook_sheets,
)


def _minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _norm_show(s: str) -> str:
    return " ".join(str(s).replace("\xa0", " ").split()).strip()


def _is_series_episode_code(code: str) -> bool:
    c = str(code).strip().upper()
    if not c or c == "MOVIE":
        return False
    if any(x in c for x in ("PAID", "PROGRAMMING", "MINISTRIES", "HOPE", "AWAKENING")):
        return False
    return True


@dataclass
class Row:
    d: date
    mins: int
    show: str
    episode: str
    source: str  # "file :: sheet"


def _load_workbook_rows(path: Path) -> list[Row]:
    out: list[Row] = []
    sheets = read_binge_workbook_sheets(path, skip_notes=True)
    for sn, df in sheets.items():
        df = normalize_binge_df_columns(df)
        try:
            c_date = _find_col(df, "DATE")
            c_start = _find_col(df, "START TIME")
            c_show = _find_col(df, "SHOW")
            c_ep = _find_col(df, "EPISODE")
        except KeyError as e:
            print(f"  skip sheet {sn!r}: {e}", file=sys.stderr)
            continue
        tag = f"{path.name} :: {sn}"
        for _, r in df.iterrows():
            try:
                d = parse_binge_date_cell(r[c_date])
            except Exception:
                continue
            try:
                st = parse_binge_time_cell(r[c_start])
            except Exception:
                continue
            show = _norm_show(str(r[c_show]) if pd.notna(r[c_show]) else "")
            ep = str(r[c_ep]).strip() if pd.notna(r[c_ep]) else ""
            out.append(Row(d, _minutes(st), show, ep, tag))
    return out


def _gather(paths: list[Path]) -> tuple[list[Row], list[str]]:
    rows: list[Row] = []
    scanned: list[str] = []
    for p in paths:
        if p.is_file() and p.suffix.lower() == ".xlsx":
            if "grids" in p.name.lower():
                continue
            scanned.append(str(p.resolve()))
            rows.extend(_load_workbook_rows(p))
        elif p.is_dir():
            for f in sorted(p.glob("*.xlsx")):
                if "grids" in f.name.lower():
                    continue
                if "binge" not in f.name.lower():
                    continue
                scanned.append(str(f.resolve()))
                rows.extend(_load_workbook_rows(f))
    return rows, scanned


@dataclass
class PairResult:
    sunday: date
    monday: date
    show: str
    sun_codes: list[str]
    mon_codes: list[str]
    expected_mon: list[str]
    ok: bool
    note: str = ""


@dataclass
class AuditReport:
    files_scanned: list[str] = field(default_factory=list)
    total_rows: int = 0
    sunday_monday_pairs: list[tuple[date, date]] = field(default_factory=list)
    results: list[PairResult] = field(default_factory=list)
    skipped_no_monday_data: list[tuple[date, str]] = field(default_factory=list)


SUN_EVENING = (20 * 60, 24 * 60)  # [20:00, 24:00)
MON_EARLY = (0, 4 * 60)  # [0:00, 4:00)


def audit(rows: list[Row]) -> AuditReport:
    rep = AuditReport()
    rep.total_rows = len(rows)

    by_day: dict[date, list[Row]] = defaultdict(list)
    for r in rows:
        by_day[r.d].append(r)

    dates = sorted(by_day.keys())
    seen_pairs: set[tuple[date, date]] = set()

    for d in dates:
        if d.weekday() != 6:  # Sunday
            continue
        m = d + timedelta(days=1)
        if m not in by_day:
            rep.skipped_no_monday_data.append((d, f"No rows for Monday {m.isoformat()} in merged data"))
            continue
        seen_pairs.add((d, m))

    rep.sunday_monday_pairs = sorted(seen_pairs)

    # Index: (sunday, normalized show) -> list of rows sorted by time
    for d, m in rep.sunday_monday_pairs:
        sun_rows = [r for r in by_day[d] if SUN_EVENING[0] <= r.mins < SUN_EVENING[1]]
        mon_rows = [r for r in by_day[m] if MON_EARLY[0] <= r.mins < MON_EARLY[1]]

        by_show_sun: dict[str, list[Row]] = defaultdict(list)
        by_show_mon: dict[str, list[Row]] = defaultdict(list)
        for r in sun_rows:
            if not r.show:
                continue
            by_show_sun[_norm_show(r.show)].append(r)
        for r in mon_rows:
            if not r.show:
                continue
            by_show_mon[_norm_show(r.show)].append(r)

        shows = sorted(set(by_show_sun) | set(by_show_mon))

        for show in shows:
            sr = sorted(by_show_sun.get(show, []), key=lambda x: x.mins)
            mr = sorted(by_show_mon.get(show, []), key=lambda x: x.mins)
            sun_codes = [r.episode for r in sr if _is_series_episode_code(r.episode)]
            mon_codes = [r.episode for r in mr if _is_series_episode_code(r.episode)]

            if not mr and not sr:
                continue
            if not mr:
                continue  # Monday has no block; optional: report Sun-only
            if not sr:
                rep.results.append(
                    PairResult(
                        d,
                        m,
                        show,
                        sun_codes,
                        mon_codes,
                        [],
                        False,
                        "Monday 0–4 has rows but no Sunday 20–24 rows for this show",
                    )
                )
                continue

            n = len(mon_codes)
            if n > len(sun_codes):
                rep.results.append(
                    PairResult(
                        d,
                        m,
                        show,
                        sun_codes,
                        mon_codes,
                        [],
                        False,
                        f"Monday has {n} codes but Sunday evening only {len(sun_codes)}",
                    )
                )
                continue

            expected = sun_codes[-n:]
            ok = expected == mon_codes
            rep.results.append(
                PairResult(
                    d,
                    m,
                    show,
                    sun_codes,
                    mon_codes,
                    expected,
                    ok,
                    "" if ok else "Monday 0–4 codes != last N of Sunday 20–24",
                )
            )

    return rep


def markdown_report(rep: AuditReport, title: str, files_scanned: list[str]) -> str:
    lines: list[str] = [
        f"# {title}",
        "",
        "Generated by `scripts/audit_binge_sun_mon_invariants.py`.",
        "",
        "## Inputs",
        "",
    ]
    if files_scanned:
        lines.append("Workbooks merged (excluding `*GRIDS*.xlsx`):")
        for fp in files_scanned:
            lines.append(f"- `{fp}`")
    else:
        lines.append("*(No workbook paths recorded.)*")
    lines += ["", "## Scope", ""]
    lines += [
        f"- Rows loaded: **{rep.total_rows}**",
        f"- Sunday→Monday calendar pairs with **both** days present in merged rows: **{len(rep.sunday_monday_pairs)}**",
        "",
    ]
    if rep.skipped_no_monday_data:
        lines += [
            "### Calendar gaps (cannot validate overnight rule)",
            "",
            "If Monday’s rows are not in any loaded workbook, Sun→Mon cannot be checked (typical when the repo only has "
            "**APRIL … BINGE.xlsx** through the last April ISO week tab, and **May 4+** lives in a separate list file).",
            "",
        ]
        for d, msg in rep.skipped_no_monday_data:
            lines.append(f"- **Sunday {d.isoformat()}**: {msg}")
        lines.append("")

    bad = [r for r in rep.results if not r.ok]
    good = [r for r in rep.results if r.ok]

    lines += [
        "## Invariant (definition)",
        "",
        "For each **Sunday / Monday** pair and each show with rows in **Sunday 20:00–24:00** and **Monday 0:00–4:00**,",
        "Monday’s EPISODE codes (series-only, excluding obvious non-series labels) must equal the **last N** Sunday evening codes,",
        "where **N** = number of Monday 00:00–04:00 rows for that show (often **8** half-hour slots = “replay the last 8”).",
        "",
        f"- **Checks with both Sun + Mon blocks:** {len(good) + len(bad)}",
        f"- **Pass:** {len(good)}",
        f"- **Fail:** {len(bad)}",
        "",
    ]

    if bad:
        lines += ["## Failures (detail)", ""]
        for r in bad:
            lines.append(
                f"### {r.sunday.isoformat()} → {r.monday.isoformat()} — {r.show}"
            )
            lines.append("")
            lines.append(f"- {r.note}")
            lines.append(f"- Sunday 20–24 codes ({len(r.sun_codes)}): `{r.sun_codes}`")
            lines.append(f"- Monday 0–4 codes ({len(r.mon_codes)}): `{r.mon_codes}`")
            if r.expected_mon:
                lines.append(f"- Expected (last {len(r.expected_mon)} of Sunday): `{r.expected_mon}`")
            lines.append("")

    lines += ["## Passing pairs (compact)", ""]
    for r in good:
        lines.append(
            f"- **{r.sunday.isoformat()}** → **{r.monday.isoformat()}** — **{r.show}** "
            f"({len(r.mon_codes)} slots) — Mon codes match Sun last {len(r.mon_codes)}"
        )
    lines += [
        "",
        "## What this does *not* check yet",
        "",
        "- Other shows (Carol, etc.) **only appear** in this list when they have **both** a Sunday 20–24 and Monday 0–4 block; ",
        "  if the workbook has no Monday rows for that show, the pair is omitted.",
        "- **Cross-workbook** Sun→Mon (e.g. Sun 5/3 in one file, Mon 5/4 in another) works **once both files are passed** ",
        "  to the script (merge all rows before comparing).",
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    argv = sys.argv[1:]
    if argv:
        paths = [Path(a) for a in argv]
    else:
        paths = [ROOT / "data"]

    resolved: list[Path] = []
    for p in paths:
        p = p.expanduser().resolve()
        if not p.exists():
            print(f"Not found: {p}", file=sys.stderr)
            sys.exit(1)
        resolved.append(p)

    rows, files_scanned = _gather(resolved)
    rep = audit(rows)
    rep.files_scanned = files_scanned

    out_md = ROOT / "docs" / "BINGE_OVERNIGHT_INVARIANTS_AUDIT.md"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    text = markdown_report(rep, "BINGE Sun→Mon overnight invariant audit", files_scanned)
    out_md.write_text(text, encoding="utf-8")
    print(f"Wrote {out_md}")
    bad = [r for r in rep.results if not r.ok]
    print(f"Pairs checked (with Mon 0-4 rows): {len(rep.results)}  OK: {len(rep.results) - len(bad)}  Fail: {len(bad)}")
    if rep.skipped_no_monday_data:
        print(f"Note: {len(rep.skipped_no_monday_data)} Sunday(s) had no Monday rows in merged workbooks (see report).")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
