"""Theme generation result helpers."""

from __future__ import annotations

from dataclasses import dataclass

from chaseos.models.theme import ThemePlan


@dataclass(frozen=True)
class ThemeGenerationResult:
    """Generated theme plan plus terminal-friendly description."""

    plan: ThemePlan
    description_text: str
