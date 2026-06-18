"""Deterministic verse selection and recent-reference history."""

from __future__ import annotations

import json
import random
from datetime import date
from pathlib import Path

from chaseos.models.signals import MoodWeight, PracticalSignals, StartupMode
from chaseos.storage.paths import get_chaseos_data_dir
from chaseos.verses.public_domain_verses import VERSE_CATALOG, Verse

RECENT_VERSE_LIMIT = 30


class RecentVerseStore:
    """Persist recently shown verse references to avoid short-term repeats."""

    def __init__(self, base_path: Path | str | None = None) -> None:
        self.base_path = Path(base_path) if base_path is not None else None

    @property
    def path(self) -> Path:
        return get_chaseos_data_dir(self.base_path) / "verses" / "recent_verses.json"

    def load(self) -> tuple[str, ...]:
        if not self.path.exists():
            return ()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return ()
        return tuple(str(ref) for ref in payload.get("recent_refs", ()) if str(ref).strip())

    def record(self, verse: Verse) -> None:
        refs = [verse.ref, *self.load()]
        deduped = list(dict.fromkeys(refs))[:RECENT_VERSE_LIMIT]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"recent_refs": deduped}, indent=2),
            encoding="utf-8",
        )


def select_verse(
    startup_mode: StartupMode | str,
    signals: PracticalSignals,
    run_date: date,
    recent_refs: tuple[str, ...] | list[str] = (),
) -> Verse:
    mode = _as_startup_mode(startup_mode)
    preferred = _preferred_tags(mode, signals)
    pool = [
        verse
        for verse in VERSE_CATALOG
        if any(tag in preferred for tag in verse.tone_tags) and verse.ref not in recent_refs
    ]
    if not pool:
        pool = [verse for verse in VERSE_CATALOG if verse.ref not in recent_refs]
    if not pool:
        pool = list(VERSE_CATALOG)
    rng = random.Random(f"{run_date.isoformat()}|{mode.value}|{'/'.join(preferred)}")
    return pool[rng.randrange(len(pool))]


def intention_for_verse(verse: Verse, startup_mode: StartupMode | str) -> str:
    mode = _as_startup_mode(startup_mode)
    if "peace" in verse.tone_tags or "rest" in verse.tone_tags:
        return "Start with less noise: one calm, faithful next action."
    if "diligence" in verse.tone_tags:
        return "Give the next task honest attention, not heroic pressure."
    if "courage" in verse.tone_tags:
        return "Take the first brave step before the whole path is visible."
    if "perseverance" in verse.tone_tags:
        return "Keep the work small enough to continue and real enough to matter."
    if mode == StartupMode.MOMENTUM:
        return "Let the energy become one useful move, then another."
    return "Choose the next right action with patience and clarity."


def _preferred_tags(mode: StartupMode, signals: PracticalSignals) -> tuple[str, ...]:
    if signals.mood_weight == MoodWeight.HEAVY:
        return ("peace", "hope", "rest")
    mapping = {
        StartupMode.CALM: ("peace", "rest", "hope"),
        StartupMode.GENTLE: ("peace", "rest", "gratitude"),
        StartupMode.STRUCTURED: ("diligence", "wisdom", "humility"),
        StartupMode.DEEP_WORK: ("diligence", "wisdom", "perseverance"),
        StartupMode.MOMENTUM: ("courage", "hope", "diligence"),
        StartupMode.TRIAGE: ("courage", "perseverance", "wisdom"),
    }
    return mapping[mode]


def _as_startup_mode(startup_mode: StartupMode | str) -> StartupMode:
    if isinstance(startup_mode, StartupMode):
        return startup_mode
    for mode in StartupMode:
        if mode.value == startup_mode:
            return mode
    return StartupMode.STRUCTURED
