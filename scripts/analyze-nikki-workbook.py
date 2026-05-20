"""Summarize import wizard analysis for Nikki test workbook."""
from __future__ import annotations

from pathlib import Path

from binge_schedule.content_import_wizard import analyze_sheet, load_raw_sheets

FILE = Path(r"c:\Users\h3art\Downloads\2024 Nikki Spreadsheets (2).xlsx")


def main() -> None:
    payload = FILE.read_bytes()
    sheets = load_raw_sheets(FILE.name, payload)
    included = 0
    inferred = 0
    skipped = 0
    print(f"Workbook: {FILE.name} ({len(sheets)} sheets)\n")
    for name, df in sheets.items():
        a = analyze_sheet(name, df)
        if a.get("include"):
            included += 1
            if a.get("layout") == "inferred":
                inferred += 1
        else:
            skipped += 1
        layout = a.get("layout", "header")
        mapping = a.get("suggested_mapping", {})
        title = mapping.get("title", "")
        print(
            f"{'+' if a.get('include') else '-'} {name[:40]:40} "
            f"layout={layout:8} rows={a.get('data_row_count', 0):4} "
            f"title={title!r:20} skip={a.get('skip_reason', '')}"
        )
    print(f"\nIncluded: {included} ({inferred} inferred) · Skipped: {skipped}")


if __name__ == "__main__":
    main()
