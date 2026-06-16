"""Deterministic local check-in interpreter."""

from __future__ import annotations

import re

from chaseos.interpretation.safety_rules import ensure_non_clinical_text
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


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _has_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern in text for pattern in patterns)


def _has_word(text: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", text) is not None


class LocalCheckInInterpreter:
    """Interpret private check-in text into practical work-start signals."""

    def interpret(
        self,
        raw_check_in: str,
        tags: list[str] | None = None,
        requested_need: str | None = None,
    ) -> CheckInInterpretation:
        tags = tags or []
        text = _normalize(" ".join([raw_check_in, *tags, requested_need or ""]))
        matches: list[str] = []

        if not text:
            signals = PracticalSignals(readiness=Readiness.NEEDS_STRUCTURE)
            return CheckInInterpretation(
                signals=signals,
                startup_mode=StartupMode.STRUCTURED,
                user_facing_summary=(
                    "I do not have much signal yet, so I am keeping the start structured.",
                    "The first move should be small, concrete, and easy to begin.",
                ),
                rule_matches=(),
                confidence=0.2,
            )

        energy = self._energy(text, matches)
        clarity = self._clarity(text, matches)
        pressure = self._pressure(text, matches)
        mood_weight = self._mood_weight(text, matches)
        focus_friction = self._focus_friction(text, matches)
        body_context = self._body_context(text, matches)
        social_battery = self._social_battery(text, matches)

        readiness = self._readiness(
            text=text,
            energy=energy,
            clarity=clarity,
            pressure=pressure,
            mood_weight=mood_weight,
            focus_friction=focus_friction,
            body_context=body_context,
            matches=matches,
        )
        signals = PracticalSignals(
            energy=energy,
            clarity=clarity,
            pressure=pressure,
            mood_weight=mood_weight,
            focus_friction=focus_friction,
            body_context=body_context,
            social_battery=social_battery,
            readiness=readiness,
        )
        startup_mode = self._startup_mode(text, signals)
        summary = self._summary(signals, startup_mode)
        confidence = min(0.95, 0.35 + (len(set(matches)) * 0.08))

        return CheckInInterpretation(
            signals=signals,
            startup_mode=startup_mode,
            user_facing_summary=tuple(ensure_non_clinical_text(line) for line in summary),
            rule_matches=tuple(dict.fromkeys(matches)),
            confidence=confidence,
        )

    def _energy(self, text: str, matches: list[str]) -> EnergyLevel:
        low_patterns = (
            "tired",
            "exhausted",
            "drained",
            "wiped",
            "slept bad",
            "slept poorly",
            "no sleep",
            "low sleep",
            "sleepy",
            "fatigue",
            "foggy and tired",
        )
        high_patterns = (
            "wired",
            "energized",
            "hyped",
            "restless",
            "antsy",
            "overclocked",
            "too much coffee",
            "too much caffeine",
        )
        if _has_any(text, high_patterns):
            matches.append("high_energy")
            return EnergyLevel.HIGH
        if _has_any(text, low_patterns):
            matches.append("low_energy")
            return EnergyLevel.LOW
        return EnergyLevel.MEDIUM

    def _clarity(self, text: str, matches: list[str]) -> ClarityLevel:
        if _has_any(
            text,
            ("overwhelmed", "too much", "buried", "overloaded", "flooded", "drowning"),
        ):
            matches.append("overloaded_clarity")
            return ClarityLevel.OVERLOADED
        if _has_any(
            text,
            (
                "scattered",
                "all over",
                "too many tabs",
                "distracted",
                "unfocused",
                "jumping around",
                "loud brain",
                "brain is loud",
            ),
        ):
            matches.append("scattered_clarity")
            return ClarityLevel.SCATTERED
        if _has_any(
            text,
            ("foggy", "brain fog", "slow", "hazy", "groggy", "can't think", "cannot think"),
        ):
            matches.append("foggy_clarity")
            return ClarityLevel.FOGGY
        if _has_any(text, ("clear", "focused", "deep work", "locked in", "lock in")):
            matches.append("clear_clarity")
            return ClarityLevel.CLEAR
        return ClarityLevel.UNKNOWN

    def _pressure(self, text: str, matches: list[str]) -> PressureLevel:
        if _has_any(
            text,
            (
                "anxious",
                "anxiety",
                "stressed",
                "pressure",
                "panic",
                "urgent",
                "behind",
                "overwhelmed",
                "on fire",
                "fire",
                "chaos",
            ),
        ):
            matches.append("high_pressure")
            return PressureLevel.HIGH
        if _has_any(text, ("busy", "tense", "a lot", "full day")):
            matches.append("medium_pressure")
            return PressureLevel.MEDIUM
        if _has_any(text, ("calm", "quiet", "steady")):
            matches.append("low_pressure")
            return PressureLevel.LOW
        return PressureLevel.UNKNOWN

    def _mood_weight(self, text: str, matches: list[str]) -> MoodWeight:
        heavy_patterns = (
            "low and heavy",
            "low today",
            "feel low",
            "feeling low",
            "heavy",
            "sad",
            "discouraged",
            "don't care",
            "do not care",
            "unmotivated",
            "numb",
            "depressed",
            "depression",
        )
        if _has_any(text, heavy_patterns):
            matches.append("heavy_mood")
            return MoodWeight.HEAVY
        if _has_any(text, ("good", "light", "optimistic", "ready")):
            matches.append("light_mood")
            return MoodWeight.LIGHT
        return MoodWeight.NEUTRAL

    def _focus_friction(self, text: str, matches: list[str]) -> FocusFriction:
        if _has_any(text, ("avoiding", "putting off", "dread", "don't want to", "do not want to")):
            matches.append("avoiding_friction")
            return FocusFriction.AVOIDING
        if _has_any(text, ("switching", "context switching", "bouncing", "interruptions")):
            matches.append("switching_friction")
            return FocusFriction.SWITCHING
        if _has_any(text, ("finishing", "follow through", "loose ends", "wrap up")):
            matches.append("finishing_friction")
            return FocusFriction.FINISHING
        if _has_any(
            text,
            (
                "priority",
                "prioritize",
                "too many things",
                "what first",
                "where to start",
                "loud brain",
                "brain is loud",
            ),
        ):
            matches.append("prioritizing_friction")
            return FocusFriction.PRIORITIZING
        if _has_any(
            text,
            (
                "can't start",
                "cannot start",
                "hard to start",
                "stuck",
                "need to start",
                "procrastinating",
            ),
        ):
            matches.append("starting_friction")
            return FocusFriction.STARTING
        if _has_any(text, ("focused", "clear", "ready")):
            return FocusFriction.NONE
        return FocusFriction.UNKNOWN

    def _body_context(self, text: str, matches: list[str]) -> list[str]:
        context: list[str] = []
        mapping = (
            ("low_sleep", ("slept bad", "slept poorly", "no sleep", "low sleep")),
            ("hungry", ("hungry",)),
            ("no_food", ("no food", "haven't eaten", "have not eaten")),
            ("caffeine_only", ("caffeine only", "coffee only")),
            ("too_much_caffeine", ("too much caffeine", "too much coffee")),
            ("headache", ("headache", "migraine")),
            ("sensory_load", ("sensory", "bright lights", "too much noise", "noise")),
            ("fatigue", ("tired", "fatigue", "exhausted", "drained")),
            ("pain", ("pain",)),
            ("sick", ("sick",)),
            ("nauseous", ("nauseous", "nausea")),
            ("hydrated", ("hydrated", "water")),
            ("restless_body", ("restless", "antsy")),
        )
        for label, patterns in mapping:
            if _has_any(text, patterns):
                context.append(label)
                matches.append(f"body_{label}")
        return list(dict.fromkeys(context))

    def _social_battery(self, text: str, matches: list[str]) -> SocialBattery:
        if _has_any(text, ("drained by people", "don't want to talk", "do not want to talk")):
            matches.append("low_social_battery")
            return SocialBattery.LOW
        if _has_any(text, ("people", "meetings", "calls", "social", "customers", "users")):
            matches.append("medium_social_battery")
            return SocialBattery.MEDIUM
        return SocialBattery.UNKNOWN

    def _readiness(
        self,
        text: str,
        energy: EnergyLevel,
        clarity: ClarityLevel,
        pressure: PressureLevel,
        mood_weight: MoodWeight,
        focus_friction: FocusFriction,
        body_context: list[str],
        matches: list[str],
    ) -> Readiness:
        if _has_any(text, ("calm me down", "calm", "reduce noise", "quiet")):
            matches.append("requested_calm")
            return Readiness.NEEDS_CALM
        if _has_any(text, ("structure", "organize", "checklist", "rails")):
            matches.append("requested_structure")
            return Readiness.NEEDS_STRUCTURE
        if _has_any(text, ("get moving", "momentum", "sprint")):
            matches.append("requested_momentum")
            return Readiness.NEEDS_MOMENTUM
        if _has_any(text, ("focus", "deep work", "lock in")):
            matches.append("requested_focus")
            return Readiness.NEEDS_FOCUS

        if pressure == PressureLevel.HIGH or clarity == ClarityLevel.OVERLOADED:
            return Readiness.NEEDS_CALM
        if any(item in body_context for item in ("headache", "sensory_load", "pain", "sick")):
            return Readiness.NEEDS_CALM
        if mood_weight == MoodWeight.HEAVY and energy == EnergyLevel.LOW:
            return Readiness.NEEDS_CALM
        if clarity in {ClarityLevel.SCATTERED, ClarityLevel.FOGGY} or focus_friction in {
            FocusFriction.STARTING,
            FocusFriction.PRIORITIZING,
            FocusFriction.AVOIDING,
        }:
            return Readiness.NEEDS_STRUCTURE
        if energy == EnergyLevel.HIGH:
            return Readiness.NEEDS_MOMENTUM
        if clarity == ClarityLevel.CLEAR:
            return Readiness.READY
        return Readiness.NEEDS_STRUCTURE

    def _startup_mode(self, text: str, signals: PracticalSignals) -> StartupMode:
        urgent_work = _has_any(
            text,
            (
                "tickets",
                "ticket",
                "queue",
                "incidents",
                "outage",
                "escalation",
                "triage",
                "support",
                "users",
                "calls",
            ),
        )
        if (
            signals.mood_weight == MoodWeight.HEAVY
            and signals.energy == EnergyLevel.LOW
            and not urgent_work
        ):
            return StartupMode.GENTLE
        if (
            signals.pressure == PressureLevel.HIGH
            or signals.clarity == ClarityLevel.OVERLOADED
        ) and signals.readiness == Readiness.NEEDS_CALM:
            return StartupMode.CALM
        if signals.clarity in {
            ClarityLevel.SCATTERED,
            ClarityLevel.FOGGY,
        } or signals.focus_friction in {
            FocusFriction.STARTING,
            FocusFriction.PRIORITIZING,
        }:
            return StartupMode.STRUCTURED
        if urgent_work:
            if signals.pressure == PressureLevel.HIGH or signals.clarity == ClarityLevel.OVERLOADED:
                return StartupMode.STRUCTURED
            return StartupMode.TRIAGE
        if signals.energy == EnergyLevel.HIGH and signals.pressure != PressureLevel.HIGH:
            return StartupMode.MOMENTUM
        if signals.clarity == ClarityLevel.CLEAR and signals.readiness in {
            Readiness.READY,
            Readiness.NEEDS_FOCUS,
        }:
            return StartupMode.DEEP_WORK
        if any(item in signals.body_context for item in ("headache", "sensory_load")):
            return StartupMode.CALM
        return StartupMode.STRUCTURED

    def _summary(
        self,
        signals: PracticalSignals,
        startup_mode: StartupMode,
    ) -> tuple[str, ...]:
        friction = (
            "no major focus friction"
            if signals.focus_friction == FocusFriction.NONE
            else f"{signals.focus_friction.value} friction"
        )
        lines = [
            (
                "I'm reading today as "
                f"{signals.energy.value} energy, "
                f"{signals.clarity.value} clarity, and {friction}."
            ),
            f"I'll set this up as {startup_mode.value}: practical, low-noise, and work-facing.",
        ]
        if signals.pressure == PressureLevel.HIGH:
            lines.append("Pressure looks elevated, so I am avoiding redline chaos.")
        if signals.mood_weight == MoodWeight.HEAVY:
            lines.append(
                "Mood weight looks heavy, so the first move should stay gentle and concrete."
            )
        if any(item in signals.body_context for item in ("headache", "sensory_load", "fatigue")):
            lines.append(
                "Body load is present, so the visuals should stay sparse and low-intensity."
            )
        if len(lines) < 4:
            lines.append("Your first move should be small and concrete.")
        return tuple(lines[:4])
