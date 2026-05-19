from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Iterable, Optional


WEEKDAY_NAMES = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


@dataclass(frozen=True)
class ScheduleBlock:
    """A normalized calendar block from the React scheduler or another UI."""

    show: str
    start: datetime
    end: datetime
    episode_key: str = ""
    episode_code: str = ""
    episode_title: str = ""
    content_type: str = ""
    genre: str = ""
    grid_text: str = ""

    @property
    def duration_minutes(self) -> int:
        return max(0, int(round((self.end - self.start).total_seconds() / 60)))

    @property
    def day(self) -> date:
        return self.start.date()

    @property
    def start_minutes(self) -> int:
        return self.start.hour * 60 + self.start.minute

    @property
    def end_minutes(self) -> int:
        if self.end.date() > self.start.date():
            return 24 * 60
        return self.end.hour * 60 + self.end.minute

    @property
    def token(self) -> str:
        return _norm(self.episode_key or self.episode_code or self.episode_title)


@dataclass(frozen=True)
class SuggestedRule:
    """A rule suggestion that must be reviewed before being applied."""

    rule_type: str
    show: str
    confidence: float
    summary: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_type": self.rule_type,
            "show": self.show,
            "confidence": round(float(self.confidence), 4),
            "summary": self.summary,
            "payload": self.payload,
        }


def analyze_schedule_rules(
    raw_blocks: Iterable[dict[str, Any] | ScheduleBlock],
    *,
    catalog_rows: Optional[list[dict[str, Any]]] = None,
) -> list[SuggestedRule]:
    """Infer editable station-rule suggestions from a draft schedule.

    The analyzer is intentionally conservative: it returns suggestions and evidence,
    but callers must still ask the user to approve/edit/reject before generation.
    """
    blocks = sorted(normalize_blocks(raw_blocks), key=lambda b: (b.start, b.end, b.show))
    suggestions: list[SuggestedRule] = []
    suggestions.extend(detect_duration_rules(blocks))
    suggestions.extend(detect_literal_rules(blocks))
    suggestions.extend(detect_overnight_repeats(blocks))
    suggestions.extend(detect_repeat_previous_slot_rules(blocks))
    suggestions.extend(detect_wrap_candidates(blocks, catalog_rows or []))
    return suggestions


def normalize_blocks(raw_blocks: Iterable[dict[str, Any] | ScheduleBlock]) -> list[ScheduleBlock]:
    out: list[ScheduleBlock] = []
    for raw in raw_blocks:
        if isinstance(raw, ScheduleBlock):
            out.append(raw)
            continue
        show = _clean(raw.get("show") or raw.get("display_name") or raw.get("title") or "")
        if not show:
            continue
        start = _parse_datetime(raw.get("start"))
        end = _parse_datetime(raw.get("end"))
        if start is None or end is None or end <= start:
            continue
        out.append(
            ScheduleBlock(
                show=show,
                start=start,
                end=end,
                episode_key=_clean(raw.get("episode_key") or raw.get("episodeId") or raw.get("episode_id") or ""),
                episode_code=_clean(raw.get("episode_code") or raw.get("code") or _code_from_title(raw.get("title"))),
                episode_title=_clean(raw.get("episode_title") or raw.get("episodeTitle") or raw.get("title") or ""),
                content_type=_clean(raw.get("content_type") or raw.get("contentType") or ""),
                genre=_clean(raw.get("genre") or raw.get("semantic_group") or ""),
                grid_text=_clean(raw.get("grid_text") or raw.get("gridText") or ""),
            )
        )
    return out


def detect_duration_rules(blocks: list[ScheduleBlock]) -> list[SuggestedRule]:
    suggestions: list[SuggestedRule] = []
    by_show = _by_show(blocks)
    for show, show_blocks in by_show.items():
        durations = [b.duration_minutes for b in show_blocks if b.duration_minutes > 0]
        if len(durations) < 2:
            continue
        counts = Counter(durations)
        duration, count = counts.most_common(1)[0]
        confidence = count / len(durations)
        if confidence < 0.75:
            continue
        suggestions.append(
            SuggestedRule(
                rule_type="duration",
                show=show,
                confidence=confidence,
                summary=f"{show} usually uses {duration}-minute blocks.",
                payload={
                    "binge_row_minutes": duration,
                    "observed_blocks": len(durations),
                    "matching_blocks": count,
                    "duration_counts": dict(sorted(counts.items())),
                    "config_patch": {"binge_row_minutes": duration},
                },
            )
        )
    return suggestions


def detect_literal_rules(blocks: list[ScheduleBlock]) -> list[SuggestedRule]:
    suggestions: list[SuggestedRule] = []
    by_show = _by_show(blocks)
    for show, show_blocks in by_show.items():
        if not show_blocks:
            continue
        type_tokens = {_norm(b.content_type).replace(" ", "_") for b in show_blocks}
        genres = {_norm(b.genre) for b in show_blocks}
        titles = {_norm(b.episode_title) for b in show_blocks if b.episode_title}
        looks_literal = (
            bool(type_tokens & {"paid_programming", "literal"})
            or bool(genres & {"ministry", "paid", "travel_lifestyle"})
            or (len(show_blocks) >= 2 and len(titles) <= 1 and all(not b.episode_code for b in show_blocks))
        )
        if not looks_literal:
            continue
        confidence = 0.9 if type_tokens & {"paid_programming", "literal"} else 0.75
        suggestions.append(
            SuggestedRule(
                rule_type="literal_content",
                show=show,
                confidence=confidence,
                summary=f"{show} appears to be fixed/literal content and should not advance through episodes.",
                payload={
                    "content_type": "literal" if "literal" in type_tokens else "paid_programming",
                    "observed_blocks": len(show_blocks),
                    "genres": sorted(g for g in genres if g),
                    "config_patch": {"kind": "literal"},
                },
            )
        )
    return suggestions


def detect_overnight_repeats(blocks: list[ScheduleBlock]) -> list[SuggestedRule]:
    candidates = [
        ((20 * 60, 24 * 60), (0, 4 * 60), "default"),
        ((18 * 60, 22 * 60), (0, 4 * 60), "mccoys"),
        ((22 * 60, 24 * 60), (4 * 60, 6 * 60), "mccoys"),
    ]
    matches: dict[tuple[str, tuple[int, int], tuple[int, int], str], list[date]] = defaultdict(list)
    for show, show_blocks in _by_show(blocks).items():
        dates = sorted({b.day for b in show_blocks})
        for target_day in dates:
            prior_day = target_day - timedelta(days=1)
            for source_window, target_window, pattern in candidates:
                source = _blocks_in_window(show_blocks, prior_day, *source_window)
                target = _blocks_in_window(show_blocks, target_day, *target_window)
                if _same_sequence(source, target):
                    matches[(show, source_window, target_window, pattern)].append(target_day)

    suggestions: list[SuggestedRule] = []
    for (show, source_window, target_window, pattern), days in sorted(matches.items()):
        if not days:
            continue
        confidence = min(0.98, 0.68 + (len(days) * 0.08))
        source_label = _window_label(*source_window)
        target_label = _window_label(*target_window)
        weekdays = sorted({WEEKDAY_NAMES[d.weekday()] for d in days}, key=WEEKDAY_NAMES.index)
        suggestions.append(
            SuggestedRule(
                rule_type="overnight_repeat",
                show=show,
                confidence=confidence,
                summary=(
                    f"{show} appears to repeat the prior day's {source_label} block "
                    f"from {target_label}."
                ),
                payload={
                    "source_window": source_label,
                    "target_window": target_label,
                    "morning_weekdays": weekdays,
                    "matched_dates": [d.isoformat() for d in days],
                    "config_patch": {
                        "overnight_repeat_after": "daily",
                        "overnight_repeat_pattern": pattern,
                        "overnight_repeat_morning_weekdays": weekdays,
                    },
                },
            )
        )
    return suggestions


def detect_repeat_previous_slot_rules(blocks: list[ScheduleBlock]) -> list[SuggestedRule]:
    suggestions: list[SuggestedRule] = []
    for show, show_blocks in _by_show(blocks).items():
        ordered = sorted(show_blocks, key=lambda b: (b.start, b.end))
        repeats = 0
        adjacent = 0
        examples: list[dict[str, str]] = []
        for prev, cur in zip(ordered, ordered[1:]):
            if prev.end != cur.start:
                continue
            adjacent += 1
            if prev.token and prev.token == cur.token:
                repeats += 1
                if len(examples) < 5:
                    examples.append({"start": cur.start.isoformat(), "episode": cur.episode_code or cur.episode_title})
        if adjacent < 2 or repeats < 2:
            continue
        confidence = repeats / adjacent
        if confidence < 0.5:
            continue
        suggestions.append(
            SuggestedRule(
                rule_type="repeat_previous_slot",
                show=show,
                confidence=confidence,
                summary=f"{show} sometimes repeats the previous adjacent slot instead of advancing episodes.",
                payload={
                    "adjacent_same_show_pairs": adjacent,
                    "repeat_pairs": repeats,
                    "examples": examples,
                    "config_patch": {"repeat_previous_slot_when_unmapped": True},
                },
            )
        )
    return suggestions


def detect_wrap_candidates(blocks: list[ScheduleBlock], catalog_rows: list[dict[str, Any]]) -> list[SuggestedRule]:
    if not catalog_rows:
        return []
    order_by_show: dict[str, dict[str, int]] = defaultdict(dict)
    for idx, row in enumerate(catalog_rows):
        show = _clean(row.get("display_name"))
        if not show:
            continue
        for token in (row.get("episode_key"), row.get("episode_code"), row.get("episode_title")):
            key = _norm(token)
            if key and key not in order_by_show[show]:
                order_by_show[show][key] = idx

    suggestions: list[SuggestedRule] = []
    for show, show_blocks in _by_show(blocks).items():
        order = order_by_show.get(show)
        if not order:
            continue
        indexes = [order[b.token] for b in sorted(show_blocks, key=lambda b: b.start) if b.token in order]
        if len(indexes) < 3:
            continue
        wraps = sum(1 for prev, cur in zip(indexes, indexes[1:]) if cur < prev)
        if wraps <= 0:
            continue
        suggestions.append(
            SuggestedRule(
                rule_type="wrap_episodes",
                show=show,
                confidence=min(0.9, 0.65 + wraps * 0.1),
                summary=f"{show} appears to restart at the beginning of its episode list.",
                payload={
                    "wrap_count": wraps,
                    "observed_episode_positions": indexes,
                    "config_patch": {"wrap_episodes": True},
                },
            )
        )
    return suggestions


def _by_show(blocks: list[ScheduleBlock]) -> dict[str, list[ScheduleBlock]]:
    out: dict[str, list[ScheduleBlock]] = defaultdict(list)
    for block in blocks:
        out[block.show].append(block)
    return out


def _blocks_in_window(blocks: list[ScheduleBlock], day: date, start_min: int, end_min: int) -> list[ScheduleBlock]:
    return sorted(
        [
            b
            for b in blocks
            if b.day == day and b.start_minutes >= start_min and b.end_minutes <= end_min
        ],
        key=lambda b: (b.start, b.end),
    )


def _same_sequence(source: list[ScheduleBlock], target: list[ScheduleBlock]) -> bool:
    if not source or len(source) != len(target):
        return False
    source_tokens = [b.token for b in source]
    target_tokens = [b.token for b in target]
    return all(source_tokens) and source_tokens == target_tokens


def _parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        if raw.endswith("Z"):
            raw = f"{raw[:-1]}+00:00"
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None
    return None


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\xa0", " ").split()).strip()


def _norm(value: Any) -> str:
    return _clean(value).casefold()


def _code_from_title(value: Any) -> str:
    title = _clean(value)
    if not title:
        return ""
    first = title.split(" ", 1)[0].strip()
    return first if any(ch.isdigit() for ch in first) else ""


def _window_label(start_min: int, end_min: int) -> str:
    return f"{_clock_label(start_min)}-{_clock_label(end_min)}"


def _clock_label(minutes: int) -> str:
    if minutes == 24 * 60:
        return "24:00"
    t = time(hour=minutes // 60, minute=minutes % 60)
    return t.strftime("%H:%M")
