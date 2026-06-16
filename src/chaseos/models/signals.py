"""Practical non-clinical signal models for ChaseOS."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class EnergyLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class ClarityLevel(StrEnum):
    CLEAR = "clear"
    FOGGY = "foggy"
    SCATTERED = "scattered"
    OVERLOADED = "overloaded"
    UNKNOWN = "unknown"


class PressureLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class MoodWeight(StrEnum):
    LIGHT = "light"
    NEUTRAL = "neutral"
    HEAVY = "heavy"
    UNKNOWN = "unknown"


class FocusFriction(StrEnum):
    STARTING = "starting"
    SWITCHING = "switching"
    FINISHING = "finishing"
    PRIORITIZING = "prioritizing"
    AVOIDING = "avoiding"
    NONE = "none"
    UNKNOWN = "unknown"


class SocialBattery(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class Readiness(StrEnum):
    NEEDS_CALM = "needs_calm"
    NEEDS_STRUCTURE = "needs_structure"
    NEEDS_MOMENTUM = "needs_momentum"
    NEEDS_FOCUS = "needs_focus"
    READY = "ready"
    UNKNOWN = "unknown"


class StartupMode(StrEnum):
    CALM = "Calm Start"
    STRUCTURED = "Structured Start"
    GENTLE = "Gentle Start"
    MOMENTUM = "Momentum Start"
    DEEP_WORK = "Deep Work Start"
    TRIAGE = "Triage Start"


class PracticalSignals(BaseModel):
    """Allowed practical signals derived from a private check-in."""

    energy: EnergyLevel = EnergyLevel.UNKNOWN
    clarity: ClarityLevel = ClarityLevel.UNKNOWN
    pressure: PressureLevel = PressureLevel.UNKNOWN
    mood_weight: MoodWeight = MoodWeight.UNKNOWN
    focus_friction: FocusFriction = FocusFriction.UNKNOWN
    body_context: list[str] = Field(default_factory=list)
    social_battery: SocialBattery = SocialBattery.UNKNOWN
    readiness: Readiness = Readiness.UNKNOWN


class CheckInInterpretation(BaseModel):
    """Local interpretation result for a private check-in."""

    signals: PracticalSignals
    startup_mode: StartupMode
    user_facing_summary: tuple[str, ...]
    rule_matches: tuple[str, ...] = ()
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
