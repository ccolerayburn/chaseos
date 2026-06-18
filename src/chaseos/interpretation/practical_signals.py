"""Shared practical signal constants and helpers."""

from __future__ import annotations

from chaseos.models.signals import (
    CheckInInterpretation,
    ClarityLevel,
    EnergyLevel,
    FocusFriction,
    MoodWeight,
    PracticalSignals,
    PressureLevel,
    Readiness,
    SocialBattery,
    StartupMode,
)

PRACTICAL_SIGNAL_KEYS = (
    "energy",
    "clarity",
    "pressure",
    "mood_weight",
    "focus_friction",
    "body_context",
    "social_battery",
    "drive",
    "readiness",
)

ALLOWED_BODY_CONTEXT = (
    "low_sleep",
    "hungry",
    "caffeine_only",
    "too_much_caffeine",
    "headache",
    "sensory_load",
    "fatigue",
    "pain",
    "hydrated",
    "no_food",
    "restless_body",
    "sick",
    "nauseous",
)

__all__ = [
    "ALLOWED_BODY_CONTEXT",
    "PRACTICAL_SIGNAL_KEYS",
    "CheckInInterpretation",
    "ClarityLevel",
    "EnergyLevel",
    "FocusFriction",
    "MoodWeight",
    "PracticalSignals",
    "PressureLevel",
    "Readiness",
    "SocialBattery",
    "StartupMode",
]
