#!/usr/bin/env python3
"""
Scan every tab in the Nikki content workbook: inferred parser style, YAML wiring,
try-load episode count, and a short preview. Writes docs/NIKKI_WORKBOOK_TAB_AUDIT.md

Usage (from repo root):
  python scripts/audit_nikki_workbook.py [path/to/workbook.xlsx]
Default: nikki_workbook from config/april_2026.yaml
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from binge_schedule import nikki
from binge_schedule.models import ShowDef


def _workbook_path_from_config() -> Path:
    cfg_path = ROOT / "config" / "april_2026.yaml"
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    p = Path(raw["nikki_workbook"])
    if p.is_absolute():
        return p
    return (cfg_path.parent / p).resolve()


def _yaml_series_by_sheet() -> dict[str, tuple[str, str | None, str | None]]:
    """Exact ``nikki_sheet`` string -> (show_key, nikki_style or None, nikki_row_filter or None)."""
    raw = yaml.safe_load((ROOT / "config" / "april_2026.yaml").read_text(encoding="utf-8"))
    out: dict[str, tuple[str, str | None, str | None]] = {}
    for key, d in (raw.get("shows") or {}).items():
        if d.get("kind") != "series":
            continue
        sh = d.get("nikki_sheet")
        if not sh:
            continue
        rf = d.get("nikki_row_filter")
        rf_s = str(rf).strip() if rf is not None and str(rf).strip() else None
        st = d.get("nikki_style")
        st_s = str(st).strip() if st is not None and str(st).strip() else None
        out[str(sh)] = (key, st_s, rf_s)
    return out


def _preview_df(df: pd.DataFrame, max_rows: int = 12, max_cols: int = 7) -> str:
    lines: list[str] = []
    for i in range(min(max_rows, len(df))):
        bits: list[str] = []
        for j in range(min(max_cols, len(df.columns))):
            v = df.iloc[i, j]
            s = "" if pd.isna(v) else str(v).replace("\n", " ").strip()
            if len(s) > 52:
                s = s[:49] + "…"
            bits.append(s)
        if any(bits):
            lines.append(f"| r{i} | " + " | ".join(bits) + " |")
    return "\n".join(lines) if lines else "(empty preview)"


def _try_load_count(
    path: str,
    sheet: str,
    *,
    default_style: str,
    yaml_style: str | None,
    row_filter: str | None,
) -> tuple[int | None, str | None]:
    sd = ShowDef(
        key="_audit",
        display_name="_",
        kind="series",
        nikki_sheet=sheet,
        prefix="AUD",
        nikki_style=yaml_style,
    )
    actual_style = (yaml_style or "").strip() or default_style
    cols = nikki.effective_column_headers(sd, style=actual_style)
    try:
        eps = nikki.load_sheet(
            path,
            sheet,
            style=actual_style,
            prefix="AUD",
            columns=cols,
            row_filter=row_filter,
        )
        return len(eps), None
    except Exception as e:
        return None, str(e)[:200]


def main() -> int:
    wb_path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else _workbook_path_from_config()
    wb_path = wb_path.resolve()
    if not wb_path.is_file():
        print(f"Workbook not found: {wb_path}", file=sys.stderr)
        return 1

    import openpyxl

    wbo = openpyxl.load_workbook(wb_path, read_only=True)
    sheets = list(wbo.sheetnames)
    wbo.close()

    ymap = _yaml_series_by_sheet()
    out_lines: list[str] = []
    out_lines.append(f"# Nikki workbook tab audit\n")
    out_lines.append(f"**File:** `{wb_path.as_posix()}`  \n")
    out_lines.append(f"**Tab count:** {len(sheets)}  \n")
    out_lines.append(
        "Each section is one Excel tab. **Try-load** uses `binge_schedule.nikki.load_sheet` with the inferred "
        "parser style; if the tab is wired in `config/april_2026.yaml`, the YAML `nikki_row_filter` "
        "(e.g. Carol green cells) is applied for the count.\n"
    )
    out_lines.append("---\n")

    for i, sheet in enumerate(sheets, start=1):
        style = nikki.default_style_for_sheet(sheet)
        yhit = ymap.get(sheet)
        show_key, yaml_style, row_filter = (None, None, None) if yhit is None else yhit
        style = nikki.default_style_for_sheet(sheet)
        note = "NOTE" in sheet.upper() or "Note" in sheet

        out_lines.append(f"## {i}. `{sheet}`\n")
        out_lines.append(f"- **Checklist:** [ ] Reviewed parser + columns + special rules\n")
        out_lines.append(f"- **In april_2026.yaml:** {'yes → `' + show_key + '`' if show_key else 'no (add `shows:` entry if this is a series)'}\n")
        out_lines.append(f"- **Name contains NOTE/Note:** {'yes — read tab instructions' if note else 'no'}\n")
        out_lines.append(
            f"- **Parser style (default → effective):** `{style}`"
            + (f" + YAML override `{yaml_style}`" if yaml_style else "")
            + "\n"
        )
        if row_filter:
            out_lines.append(f"- **YAML `nikki_row_filter`:** `{row_filter}`\n")
        try:
            df = pd.read_excel(wb_path.as_posix(), sheet_name=sheet, header=None, nrows=45)
            out_lines.append("### Top-of-sheet preview (first non-empty rows, truncated)\n")
            out_lines.append(_preview_df(df))
            out_lines.append("\n")
        except Exception as e:
            out_lines.append(f"### Preview failed: `{e}`\n")

        n, err = _try_load_count(
            wb_path.as_posix(),
            sheet,
            default_style=style,
            yaml_style=yaml_style,
            row_filter=row_filter,
        )
        if err:
            out_lines.append(f"### Try-load episodes: **failed** — `{err}`\n")
        else:
            out_lines.append(f"### Try-load episodes: **{n}** rows parsed (with filters above if any)\n")

        out_lines.append("\n---\n")

    doc = ROOT / "docs" / "NIKKI_WORKBOOK_TAB_AUDIT.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"Wrote {doc.relative_to(ROOT)} ({len(sheets)} tabs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
