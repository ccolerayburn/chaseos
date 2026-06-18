"""Ritual stage names for the ChaseOS startup sequence."""

from __future__ import annotations

from enum import StrEnum


class RitualStage(StrEnum):
    """Text-only startup ritual stages."""

    IDLE = "IDLE"
    CHECK_IN = "CHECK_IN"
    CHECK_IN_FOLLOW_UP = "CHECK_IN_FOLLOW_UP"
    INTERPRETING = "INTERPRETING"
    THEME_PLAN = "THEME_PLAN"
    THEME_APPROVAL = "THEME_APPROVAL"
    MINDFULNESS = "MINDFULNESS"
    VERSE = "VERSE"
    INNOVATION = "INNOVATION"
    INNOVATION_TAKEAWAY = "INNOVATION_TAKEAWAY"
    POSTER_PLAN = "POSTER_PLAN"
    POSTER_APPROVAL = "POSTER_APPROVAL"
    WORK_RAMP = "WORK_RAMP"
    APPLYING = "APPLYING"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    RESET = "RESET"


RITUAL_STAGE_NAMES = tuple(stage.value for stage in RitualStage)
