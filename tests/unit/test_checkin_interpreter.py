from chaseos.interpretation.checkin_interpreter import LocalCheckInInterpreter
from chaseos.interpretation.practical_signals import PRACTICAL_SIGNAL_KEYS
from chaseos.interpretation.safety_rules import contains_forbidden_clinical_text
from chaseos.models.signals import (
    ClarityLevel,
    EnergyLevel,
    FocusFriction,
    MoodWeight,
    PressureLevel,
    StartupMode,
)


def test_practical_signal_keys_match_product_boundary() -> None:
    assert PRACTICAL_SIGNAL_KEYS == (
        "energy",
        "clarity",
        "pressure",
        "mood_weight",
        "focus_friction",
        "body_context",
        "social_battery",
        "readiness",
    )


def summary_text(lines: tuple[str, ...]) -> str:
    return "\n".join(lines)


def test_tired_foggy_scattered_input_becomes_structured_start() -> None:
    result = LocalCheckInInterpreter().interpret(
        "slept bad, foggy, hungry, scattered. need to get through tickets."
    )

    assert result.signals.energy == EnergyLevel.LOW
    assert result.signals.clarity in {ClarityLevel.FOGGY, ClarityLevel.SCATTERED}
    assert "hungry" in result.signals.body_context
    assert result.startup_mode == StartupMode.STRUCTURED


def test_wired_restless_input_becomes_momentum_start() -> None:
    result = LocalCheckInInterpreter().interpret("wired and restless but motivated")

    assert result.signals.energy == EnergyLevel.HIGH
    assert result.startup_mode == StartupMode.MOMENTUM


def test_low_heavy_input_becomes_gentle_start() -> None:
    result = LocalCheckInInterpreter().interpret("exhausted, low and heavy today")

    assert result.signals.energy == EnergyLevel.LOW
    assert result.signals.mood_weight == MoodWeight.HEAVY
    assert result.startup_mode == StartupMode.GENTLE


def test_ticket_queue_on_fire_uses_safe_urgent_start() -> None:
    result = LocalCheckInInterpreter().interpret("ticket queue is already on fire")

    assert result.signals.pressure == PressureLevel.HIGH
    assert result.startup_mode in {StartupMode.STRUCTURED, StartupMode.CALM}


def test_headache_sensory_input_sets_body_context() -> None:
    result = LocalCheckInInterpreter().interpret("headache, too much noise, bright lights")

    assert "headache" in result.signals.body_context
    assert "sensory_load" in result.signals.body_context


def test_anxious_input_reframes_as_pressure_without_clinical_output() -> None:
    result = LocalCheckInInterpreter().interpret("I feel anxious")

    assert result.signals.pressure == PressureLevel.HIGH
    assert not contains_forbidden_clinical_text(summary_text(result.user_facing_summary))


def test_depressed_input_reframes_as_heavy_mood_without_clinical_output() -> None:
    result = LocalCheckInInterpreter().interpret("I feel depressed")

    assert result.signals.mood_weight == MoodWeight.HEAVY
    assert not contains_forbidden_clinical_text(summary_text(result.user_facing_summary))


def test_adhd_input_reframes_as_focus_signal_without_clinical_output() -> None:
    result = LocalCheckInInterpreter().interpret("ADHD brain is loud today")

    assert result.signals.clarity == ClarityLevel.SCATTERED
    assert result.signals.focus_friction == FocusFriction.PRIORITIZING
    assert not contains_forbidden_clinical_text(summary_text(result.user_facing_summary))


def test_empty_input_uses_default_structured_start() -> None:
    result = LocalCheckInInterpreter().interpret("")

    assert result.signals.energy == EnergyLevel.UNKNOWN
    assert result.startup_mode == StartupMode.STRUCTURED


def test_forbidden_labels_are_not_present_in_generated_summaries() -> None:
    cases = (
        "I feel anxious",
        "I feel depressed",
        "ADHD brain is loud today",
    )

    for case in cases:
        result = LocalCheckInInterpreter().interpret(case)
        assert not contains_forbidden_clinical_text(summary_text(result.user_facing_summary))
