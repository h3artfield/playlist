"""Compare episode-action extraction across all sheets in a BINGE workbook."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from binge_schedule.binge_pattern import build_episode_actions_from_binge_df, merge_episode_action_maps
from binge_schedule.binge_to_grid import read_binge_workbook_sheets
from binge_schedule.config_io import load_build_config


def main() -> None:
    cfg = load_build_config(ROOT / "config/april_2026.yaml")
    path = Path(r"c:\Users\h3art\Downloads\APRIL 2026 BINGE.xlsx")
    sheets = read_binge_workbook_sheets(path)
    names = list(sheets.keys())
    print("Sheets:", names)

    maps = {name: build_episode_actions_from_binge_df(sheets[name], cfg) for name in names}

    base = names[0]
    for name in names[1:]:
        eq = maps[base] == maps[name]
        print(f"\n{base!r} vs {name!r}: identical actions? {eq}")
        if not eq:
            a, b = maps[base], maps[name]
            keys_a, keys_b = set(a.keys()), set(b.keys())
            print(f"  keys only in {base}: {len(keys_a - keys_b)}")
            print(f"  keys only in {name}: {len(keys_b - keys_a)}")
            diff = [k for k in sorted(keys_a & keys_b) if a[k] != b[k]]
            print(f"  keys with differing actions: {len(diff)}")
            for k in diff[:12]:
                print(f"    {k}: {a[k]!r} vs {b[k]!r}")

    merged = merge_episode_action_maps([(n, maps[n]) for n in names])
    print("\nMerged map size:", len(merged))
    tex = {k: v for k, v in merged.items() if k[0] == "texan"}
    rep = {k: v for k, v in tex.items() if v != "advance"}
    print("Texan repeat actions (sample):", list(rep.items())[:12])


if __name__ == "__main__":
    main()
