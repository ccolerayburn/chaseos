from datetime import date

from chaseos.models.signals import MoodWeight, PracticalSignals, StartupMode
from chaseos.verses.public_domain_verses import (
    KNOWN_TONE_TAGS,
    PUBLIC_DOMAIN_TRANSLATIONS,
    VERSE_CATALOG,
)
from chaseos.verses.verse_selector import RecentVerseStore, select_verse


def test_catalog_contains_only_public_domain_translations_and_known_tags() -> None:
    assert 40 <= len(VERSE_CATALOG) <= 60
    assert all(verse.translation in PUBLIC_DOMAIN_TRANSLATIONS for verse in VERSE_CATALOG)
    assert all(set(verse.tone_tags) <= KNOWN_TONE_TAGS for verse in VERSE_CATALOG)


def test_selector_avoids_recent_references_when_possible() -> None:
    first = select_verse(
        StartupMode.MOMENTUM,
        PracticalSignals(),
        date(2026, 6, 17),
    )

    second = select_verse(
        StartupMode.MOMENTUM,
        PracticalSignals(),
        date(2026, 6, 17),
        recent_refs=(first.ref,),
    )

    assert second.ref != first.ref


def test_heavy_mood_prefers_restorative_tags() -> None:
    verse = select_verse(
        StartupMode.STRUCTURED,
        PracticalSignals(mood_weight=MoodWeight.HEAVY),
        date(2026, 6, 17),
    )

    assert set(verse.tone_tags) & {"peace", "hope", "rest"}


def test_recent_verse_store_records_latest_first_and_dedupes(tmp_path) -> None:
    store = RecentVerseStore(base_path=tmp_path)
    first, second = VERSE_CATALOG[0], VERSE_CATALOG[1]

    store.record(first)
    store.record(second)
    store.record(first)

    assert store.load()[:2] == (first.ref, second.ref)
