"""Deterministic text-only theme generator."""

from __future__ import annotations

from datetime import date

from chaseos.interpretation.safety_rules import ensure_non_clinical_text
from chaseos.models.signals import (
    EnergyLevel,
    PracticalSignals,
    PressureLevel,
    StartupMode,
)
from chaseos.models.theme import (
    LocalPhotoUsage,
    MonitorThemePlan,
    MotionLevel,
    PhotoUsage,
    ThemeColors,
    ThemeFamily,
    ThemePlan,
    VisualDensity,
)
from chaseos.theming.palettes import THEME_PALETTES
from chaseos.theming.theme_models import ThemeGenerationResult

THEME_STYLE_TAGS = ("cyberpunk", "minimal", "text_only")


def _as_startup_mode(startup_mode: StartupMode | str) -> StartupMode:
    if isinstance(startup_mode, StartupMode):
        return startup_mode
    for mode in StartupMode:
        if mode.value == startup_mode:
            return mode
    return StartupMode.STRUCTURED


def _has_change(change_requests: tuple[str, ...], *needles: str) -> bool:
    text = " ".join(change_requests).lower()
    return any(needle in text for needle in needles)


def _usage_label(usage: PhotoUsage) -> str:
    return {
        PhotoUsage.GENERATED: "generated",
        PhotoUsage.LOCAL_PHOTO: "local photo",
        PhotoUsage.HYBRID: "hybrid photo overlay",
    }[usage]


class ThemeGenerator:
    """Create safe cyberpunk/minimal theme plans from practical signals."""

    def generate(
        self,
        signals: PracticalSignals,
        startup_mode: StartupMode | str,
        run_date: date | None = None,
        random_salt: str | None = None,
        change_requests: list[str] | tuple[str, ...] | None = None,
        regenerate_count: int = 0,
    ) -> ThemeGenerationResult:
        del run_date, random_salt
        mode = _as_startup_mode(startup_mode)
        changes = tuple(change_requests or ())
        body_load = self._has_body_load(signals)
        family = self._select_family(signals, mode, changes, regenerate_count)
        colors = self._colors(family, changes)
        intensity = self._intensity(signals, mode, changes)
        density = self._density(signals, mode, changes)
        motion = self._motion(mode, density, body_load, changes)
        photo_usage = self._photo_usage(signals, mode, changes)
        monitor_plan = MonitorThemePlan(
            display_1="public generated art",
            display_4=f"left atmosphere, {_usage_label(photo_usage.display_4)}",
            display_2="center command, generated minimal",
            display_3=f"right inspiration, {_usage_label(photo_usage.display_3)} cyberpunk",
        )
        notes = self._notes(signals, mode, family, changes, body_load)

        palette = THEME_PALETTES[family]
        plan = ThemePlan(
            startup_mode=mode.value,
            family=family,
            palette_label=str(palette["label"]),
            colors=colors,
            cyberpunk_intensity=intensity,
            visual_density=density,
            motion=motion,
            icon_style=self._icon_style(family, changes),
            local_photo_usage=photo_usage,
            monitor_plan=monitor_plan,
            notes=notes,
        )
        description = self.describe(plan)
        return ThemeGenerationResult(plan=plan, description_text=description)

    def describe(self, plan: ThemePlan) -> str:
        intensity = round(plan.cyberpunk_intensity * 100)
        lines = [
            "THEME PLAN",
            f"mode ............ {plan.startup_mode}",
            f"family .......... {plan.family.value}",
            f"palette ......... {plan.palette_label}",
            f"intensity ....... {intensity}%",
            f"density ......... {plan.visual_density.value}",
            f"motion .......... {plan.motion.value}",
            f"icons ........... {plan.icon_style}",
            f"display 1 ....... {plan.monitor_plan.display_1}",
            f"display 4 ....... {plan.monitor_plan.display_4}",
            f"display 2 ....... {plan.monitor_plan.display_2}",
            f"display 3 ....... {plan.monitor_plan.display_3}",
        ]
        if plan.notes:
            lines.append("")
            lines.append("NOTES")
            lines.extend(f"- {note}" for note in plan.notes)
        return ensure_non_clinical_text("\n".join(lines))

    def _select_family(
        self,
        signals: PracticalSignals,
        mode: StartupMode,
        changes: tuple[str, ...],
        regenerate_count: int,
    ) -> ThemeFamily:
        body_load = self._has_body_load(signals)
        pressure_high = signals.pressure == PressureLevel.HIGH
        by_mode = {
            StartupMode.CALM: (ThemeFamily.SYNTH_SANCTUARY, ThemeFamily.ARCTIC_INTERFACE),
            StartupMode.STRUCTURED: (
                ThemeFamily.OBSIDIAN_TERMINAL,
                ThemeFamily.CHROME_MONOLITH,
            ),
            StartupMode.GENTLE: (ThemeFamily.SYNTH_SANCTUARY, ThemeFamily.SYNTHETIC_SUNRISE),
            StartupMode.MOMENTUM: (ThemeFamily.NEON_NOIR, ThemeFamily.VIOLET_CIRCUIT),
            StartupMode.DEEP_WORK: (
                ThemeFamily.CHROME_MONOLITH,
                ThemeFamily.OBSIDIAN_TERMINAL,
            ),
            StartupMode.TRIAGE: (
                (ThemeFamily.OBSIDIAN_TERMINAL, ThemeFamily.SYNTH_SANCTUARY)
                if pressure_high
                else (ThemeFamily.REDLINE_PROTOCOL, ThemeFamily.OBSIDIAN_TERMINAL)
            ),
        }
        candidates = by_mode[mode]
        if _has_change(changes, "ff7", "mako"):
            candidates = (ThemeFamily.MAKO_REACTOR,)
        elif _has_change(changes, "lofi"):
            candidates = (ThemeFamily.LOFI_DUSK,)
        elif _has_change(changes, "calmer", "more calm", "tone it down", "less intense"):
            candidates = (
                ThemeFamily.LOFI_DUSK,
                ThemeFamily.SYNTH_SANCTUARY,
                ThemeFamily.ARCTIC_INTERFACE,
            )
        elif _has_change(changes, "more cyberpunk", "more futuristic", "more neon") and not (
            body_load or pressure_high
        ):
            candidates = (
                ThemeFamily.DUSK_SKYLINE,
                ThemeFamily.NEON_NOIR,
                ThemeFamily.VIOLET_CIRCUIT,
            )
        return candidates[regenerate_count % len(candidates)]

    def _colors(self, family: ThemeFamily, changes: tuple[str, ...]) -> ThemeColors:
        colors = THEME_PALETTES[family]["colors"].model_copy()
        if _has_change(changes, "ff7", "mako"):
            colors = THEME_PALETTES[ThemeFamily.MAKO_REACTOR]["colors"].model_copy()
        if _has_change(changes, "lofi"):
            colors = THEME_PALETTES[ThemeFamily.LOFI_DUSK]["colors"].model_copy()
        if _has_change(changes, "more yellow"):
            colors.primary = "#c6a452"
            colors.accent = "#d6a73d"
            colors.text = "#d8bd69"
        if _has_change(changes, "less cyan"):
            colors.secondary = "#687077"
            if colors.accent.lower() in {"#6fb3bd", "#1fb8d1"}:
                colors.accent = "#b08a2e"
        if _has_change(changes, "darker"):
            colors.background = "#121212"
            colors.surface = "#1c1c1c"
        if _has_change(changes, "brighter"):
            colors.surface = "#303030"
        if _has_change(changes, "more contrast"):
            colors.accent = "#e0b447"
        if _has_change(changes, "less contrast"):
            colors.accent = "#a88a49"
        return colors

    def _intensity(
        self,
        signals: PracticalSignals,
        mode: StartupMode,
        changes: tuple[str, ...],
    ) -> float:
        base = {
            StartupMode.CALM: 0.25,
            StartupMode.STRUCTURED: 0.42,
            StartupMode.GENTLE: 0.18,
            StartupMode.MOMENTUM: 0.68,
            StartupMode.DEEP_WORK: 0.35,
            StartupMode.TRIAGE: 0.55,
        }[mode]
        if signals.pressure == PressureLevel.HIGH:
            base = min(base, 0.45)
        if self._has_body_load(signals):
            base = min(base, 0.28)
        if any(item in signals.body_context for item in ("low_sleep", "fatigue")):
            base = min(base, 0.35)
        if _has_change(changes, "calmer", "more calm", "tone it down", "less intense"):
            base = max(0.12, base - 0.18)
        if _has_change(changes, "more cyberpunk", "more futuristic", "more neon", "more geometry"):
            cap = (
                0.45
                if self._has_body_load(signals) or signals.pressure == PressureLevel.HIGH
                else 0.82
            )
            base = min(cap, base + 0.18)
        return round(max(0.0, min(1.0, base)), 2)

    def _density(
        self,
        signals: PracticalSignals,
        mode: StartupMode,
        changes: tuple[str, ...],
    ) -> VisualDensity:
        density = {
            StartupMode.CALM: VisualDensity.SPARSE,
            StartupMode.STRUCTURED: VisualDensity.SPARSE,
            StartupMode.GENTLE: VisualDensity.VERY_SPARSE,
            StartupMode.MOMENTUM: VisualDensity.MEDIUM,
            StartupMode.DEEP_WORK: VisualDensity.VERY_SPARSE,
            StartupMode.TRIAGE: VisualDensity.MEDIUM,
        }[mode]
        if self._has_body_load(signals) or "low_sleep" in signals.body_context:
            density = VisualDensity.VERY_SPARSE
        if _has_change(changes, "less visual noise", "more minimal", "calmer", "tone it down"):
            density = VisualDensity.VERY_SPARSE
        if _has_change(
            changes, "more cyberpunk", "more neon", "more geometry"
        ) and not self._has_body_load(signals):
            density = VisualDensity.MEDIUM
        return density

    def _motion(
        self,
        mode: StartupMode,
        density: VisualDensity,
        body_load: bool,
        changes: tuple[str, ...],
    ) -> MotionLevel:
        if body_load or density == VisualDensity.VERY_SPARSE:
            return MotionLevel.NONE
        if _has_change(changes, "calmer", "tone it down", "less visual noise"):
            return MotionLevel.NONE
        if mode == StartupMode.MOMENTUM:
            return MotionLevel.NORMAL
        return MotionLevel.MINIMAL

    def _photo_usage(
        self,
        signals: PracticalSignals,
        mode: StartupMode,
        changes: tuple[str, ...],
    ) -> LocalPhotoUsage:
        body_load = self._has_body_load(signals)
        usage = LocalPhotoUsage(
            display_4=PhotoUsage.GENERATED if body_load else PhotoUsage.HYBRID,
            display_2=PhotoUsage.GENERATED,
            display_3=(
                PhotoUsage.HYBRID
                if (
                    mode == StartupMode.MOMENTUM
                    and signals.energy == EnergyLevel.HIGH
                    and not body_load
                )
                else PhotoUsage.GENERATED
            ),
        )
        if _has_change(changes, "use more local photos", "more local photos") and not body_load:
            usage.display_4 = PhotoUsage.HYBRID
            usage.display_3 = PhotoUsage.LOCAL_PHOTO
        if _has_change(changes, "no photos today", "generated only", "no photos"):
            usage.display_4 = PhotoUsage.GENERATED
            usage.display_2 = PhotoUsage.GENERATED
            usage.display_3 = PhotoUsage.GENERATED
        return usage

    def _icon_style(self, family: ThemeFamily, changes: tuple[str, ...]) -> str:
        if _has_change(changes, "more yellow"):
            return "thin-line amber/gold"
        if family in {ThemeFamily.NEON_NOIR, ThemeFamily.VIOLET_CIRCUIT, ThemeFamily.DUSK_SKYLINE}:
            return "thin-line violet/cyan"
        if family == ThemeFamily.MAKO_REACTOR:
            return "thin-line mako teal/amber"
        if family == ThemeFamily.LOFI_DUSK:
            return "thin-line warm amber/cool blue"
        if family == ThemeFamily.REDLINE_PROTOCOL:
            return "thin-line amber/red"
        return "thin-line amber/cyan"

    def _notes(
        self,
        signals: PracticalSignals,
        mode: StartupMode,
        family: ThemeFamily,
        changes: tuple[str, ...],
        body_load: bool,
    ) -> list[str]:
        notes: list[str] = []
        if mode == StartupMode.STRUCTURED:
            notes.append("center display stays low-noise for ticket work.")
        if signals.pressure == PressureLevel.HIGH:
            notes.append("pressure is elevated, so redline styling is disabled.")
        if body_load:
            notes.append("body load is present, so density and motion are reduced.")
        if family == ThemeFamily.MAKO_REACTOR:
            notes.append("mako teal-green accents are available for Display 1 art.")
        if family == ThemeFamily.LOFI_DUSK:
            notes.append("lofi dusk warmth is available for Display 1 art.")
        if family == ThemeFamily.REDLINE_PROTOCOL:
            notes.append("redline accents are used only because pressure is not high.")
        if _has_change(changes, "use more local photos", "more local photos") and body_load:
            notes.append("local photo usage stayed limited to protect a low-noise setup.")
        if _has_change(changes, "no photos today", "generated only", "no photos"):
            notes.append("private displays are generated-only for today.")
        return notes

    def _has_body_load(self, signals: PracticalSignals) -> bool:
        return any(
            item in signals.body_context for item in ("headache", "sensory_load", "pain", "sick")
        )
