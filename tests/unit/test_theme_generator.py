from chaseos.interpretation.safety_rules import contains_forbidden_clinical_text
from chaseos.models.signals import (
    ClarityLevel,
    EnergyLevel,
    PracticalSignals,
    PressureLevel,
    StartupMode,
)
from chaseos.models.theme import PhotoUsage, ThemeFamily, VisualDensity
from chaseos.theming.theme_generator import THEME_STYLE_TAGS, ThemeGenerator


def test_theme_generation_is_text_first() -> None:
    assert "cyberpunk" in THEME_STYLE_TAGS
    assert "minimal" in THEME_STYLE_TAGS
    assert "text_only" in THEME_STYLE_TAGS


def generate(signals: PracticalSignals, mode: StartupMode, **kwargs):
    return ThemeGenerator().generate(signals, mode, **kwargs)


def test_calm_start_uses_calm_family_and_low_intensity() -> None:
    result = generate(PracticalSignals(pressure=PressureLevel.HIGH), StartupMode.CALM)

    assert result.plan.family in {ThemeFamily.SYNTH_SANCTUARY, ThemeFamily.ARCTIC_INTERFACE}
    assert result.plan.cyberpunk_intensity <= 0.45


def test_structured_start_uses_terminal_or_monolith() -> None:
    result = generate(PracticalSignals(clarity=ClarityLevel.SCATTERED), StartupMode.STRUCTURED)

    assert result.plan.family in {ThemeFamily.OBSIDIAN_TERMINAL, ThemeFamily.CHROME_MONOLITH}


def test_gentle_start_uses_soft_family() -> None:
    result = generate(PracticalSignals(energy=EnergyLevel.LOW), StartupMode.GENTLE)

    assert result.plan.family in {ThemeFamily.SYNTH_SANCTUARY, ThemeFamily.SYNTHETIC_SUNRISE}


def test_momentum_start_uses_neon_family_without_constraints() -> None:
    result = generate(PracticalSignals(energy=EnergyLevel.HIGH), StartupMode.MOMENTUM)

    assert result.plan.family in {ThemeFamily.NEON_NOIR, ThemeFamily.VIOLET_CIRCUIT}


def test_triage_with_high_pressure_does_not_use_redline_protocol() -> None:
    result = generate(PracticalSignals(pressure=PressureLevel.HIGH), StartupMode.TRIAGE)

    assert result.plan.family != ThemeFamily.REDLINE_PROTOCOL


def test_headache_sensory_lowers_intensity_and_density() -> None:
    result = generate(
        PracticalSignals(body_context=["headache", "sensory_load"]),
        StartupMode.MOMENTUM,
    )

    assert result.plan.cyberpunk_intensity <= 0.28
    assert result.plan.visual_density == VisualDensity.VERY_SPARSE


def test_display_one_is_always_public_innovation_poster() -> None:
    result = generate(PracticalSignals(), StartupMode.STRUCTURED)

    assert result.plan.monitor_plan.display_1 == "public innovation poster"


def test_display_two_is_generated_minimal_by_default() -> None:
    result = generate(PracticalSignals(), StartupMode.STRUCTURED)

    assert result.plan.local_photo_usage.display_2 == PhotoUsage.GENERATED
    assert "center command, generated minimal" in result.description_text


def test_change_more_cyberpunk_increases_intensity_within_constraints() -> None:
    base = generate(PracticalSignals(), StartupMode.STRUCTURED)
    changed = generate(
        PracticalSignals(),
        StartupMode.STRUCTURED,
        change_requests=["more cyberpunk"],
    )

    assert changed.plan.cyberpunk_intensity > base.plan.cyberpunk_intensity


def test_change_calmer_lowers_intensity_and_density() -> None:
    base = generate(PracticalSignals(energy=EnergyLevel.HIGH), StartupMode.MOMENTUM)
    changed = generate(
        PracticalSignals(energy=EnergyLevel.HIGH),
        StartupMode.MOMENTUM,
        change_requests=["calmer"],
    )

    assert changed.plan.cyberpunk_intensity < base.plan.cyberpunk_intensity
    assert changed.plan.visual_density == VisualDensity.VERY_SPARSE


def test_change_use_more_local_photos_affects_private_side_displays_only() -> None:
    result = generate(
        PracticalSignals(),
        StartupMode.STRUCTURED,
        change_requests=["use more local photos"],
    )

    assert result.plan.local_photo_usage.display_4 == PhotoUsage.HYBRID
    assert result.plan.local_photo_usage.display_3 == PhotoUsage.LOCAL_PHOTO
    assert result.plan.local_photo_usage.display_2 == PhotoUsage.GENERATED
    assert result.plan.monitor_plan.display_1 == "public innovation poster"


def test_change_no_photos_today_makes_private_displays_generated() -> None:
    result = generate(
        PracticalSignals(),
        StartupMode.STRUCTURED,
        change_requests=["no photos today"],
    )

    assert result.plan.local_photo_usage.display_4 == PhotoUsage.GENERATED
    assert result.plan.local_photo_usage.display_2 == PhotoUsage.GENERATED
    assert result.plan.local_photo_usage.display_3 == PhotoUsage.GENERATED


def test_regenerate_returns_valid_alternate_theme_plan() -> None:
    first = generate(PracticalSignals(), StartupMode.STRUCTURED, regenerate_count=0)
    second = generate(PracticalSignals(), StartupMode.STRUCTURED, regenerate_count=1)

    assert second.plan.family != first.plan.family
    assert second.description_text.startswith("THEME PLAN")


def test_theme_description_contains_monitor_roles_and_no_private_check_in() -> None:
    raw_check_in = "tired and scattered with a private detail"
    result = generate(PracticalSignals(), StartupMode.STRUCTURED)

    assert "display 1" in result.description_text
    assert "display 4" in result.description_text
    assert raw_check_in not in result.description_text
    assert not contains_forbidden_clinical_text(result.description_text)
