"""Rebuild and normalize content-workbook episodes for archive / UI display."""

from __future__ import annotations

import re
from typing import Any, Optional

from binge_schedule.models import Episode

_COMPOSITE_CODE_STYLES = frozenset(
    {
        "texan",
        "renegade",
        "real_mccoys",
        "carol_burnett",
        "mst3k",
        "saint",
        "laugh_in",
        "leading_episode",
        "jim_bowie",
    }
)


def _normalize_text(s: str) -> str:
    return " ".join(str(s).replace("\xa0", " ").split()).strip()


def season_episode_parts(ep: Episode, style: str) -> tuple[Optional[int], Optional[int]]:
    """Infer (season, episode_in_season) for grouping and S×E labels."""
    se = _normalize_text(ep.season_ep or "")
    if se:
        m = re.match(r"S(\d+)\s*[_ ]?\s*E(\d+)", se, re.I)
        if m:
            return int(m.group(1)), int(m.group(2))
        parts = re.split(r"[_/]", se)
        if len(parts) == 2:
            try:
                return int(parts[0]), int(parts[1])
            except ValueError:
                pass
    n = ep.episode_num
    if n is not None and style in _COMPOSITE_CODE_STYLES and n >= 101:
        return n // 100, n % 100
    if n is not None:
        return None, int(n)
    return None, None


def _se_compact(idx0: int, season: Optional[int], ep_in_season: Optional[int]) -> str:
    if season is not None and ep_in_season is not None:
        return f"S{season:02d}E{ep_in_season:02d}"
    if ep_in_season is not None:
        return f"E{ep_in_season}"
    return f"#{idx0 + 1}"


def normalize_episodes_for_archive(episodes: list[Episode], style: str) -> list[dict[str, Any]]:
    """Return one JSON-friendly dict per row: same order as ``nikki.load_sheet`` (schedule order)."""
    out: list[dict[str, Any]] = []
    for i, ep in enumerate(episodes):
        season, ep_in_season = season_episode_parts(ep, style)
        title = _normalize_text(ep.title)
        raw_cell = _normalize_text(ep.raw)
        code = _normalize_text(ep.code or "")
        sheet_se = _normalize_text(ep.season_ep or "")
        out.append(
            {
                "idx0": i,
                "schedule_num": i + 1,
                "code": code,
                "title": title,
                "season": season,
                "ep_in_season": ep_in_season,
                "sheet_se": sheet_se,
                "raw_cell": raw_cell,
                "se_compact": _se_compact(i, season, ep_in_season),
                "season_key": str(season) if season is not None else "__none__",
            }
        )
    return out
