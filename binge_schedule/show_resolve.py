"""Match grid / BINGE SHOW text to configured series."""

from __future__ import annotations

from typing import Optional

from binge_schedule.models import ShowDef


def resolve_show(cell: str, shows: dict[str, ShowDef]) -> tuple[str, Optional[ShowDef]]:
    cell = cell.strip()
    for key, sd in shows.items():
        dn = sd.display_name.strip()
        if cell == dn:
            return key, sd
    candidates: list[tuple[int, str, ShowDef]] = []
    for key, sd in shows.items():
        dn = sd.display_name.strip()
        if cell.startswith(dn):
            candidates.append((len(dn), key, sd))
    if candidates:
        candidates.sort(reverse=True)
        _, key, sd = candidates[0]
        return key, sd
    return "literal", None
