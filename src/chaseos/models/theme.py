"""Theme planning models for ChaseOS."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ThemeFamily(StrEnum):
    OBSIDIAN_TERMINAL = "Obsidian Terminal"
    NEON_NOIR = "Neon Noir"
    CHROME_MONOLITH = "Chrome Monolith"
    VIOLET_CIRCUIT = "Violet Circuit"
    REDLINE_PROTOCOL = "Redline Protocol"
    ARCTIC_INTERFACE = "Arctic Interface"
    SYNTH_SANCTUARY = "Synth Sanctuary"
    SYNTHETIC_SUNRISE = "Synthetic Sunrise"
    DUSK_SKYLINE = "Dusk Skyline"
    MAKO_REACTOR = "Mako Reactor"
    LOFI_DUSK = "Lofi Dusk"


class VisualDensity(StrEnum):
    VERY_SPARSE = "very_sparse"
    SPARSE = "sparse"
    MEDIUM = "medium"
    DENSE = "dense"


class MotionLevel(StrEnum):
    NONE = "none"
    MINIMAL = "minimal"
    NORMAL = "normal"


class PhotoUsage(StrEnum):
    GENERATED = "generated"
    LOCAL_PHOTO = "local_photo"
    HYBRID = "hybrid"


class ThemeColors(BaseModel):
    background: str
    surface: str
    primary: str
    secondary: str
    accent: str
    text: str


class LocalPhotoUsage(BaseModel):
    display_4: PhotoUsage = PhotoUsage.HYBRID
    display_2: PhotoUsage = PhotoUsage.GENERATED
    display_3: PhotoUsage = PhotoUsage.GENERATED


class MonitorThemePlan(BaseModel):
    display_1: str = "public generated art"
    display_4: str = "left atmosphere"
    display_2: str = "center command"
    display_3: str = "right inspiration"


class ThemePlan(BaseModel):
    startup_mode: str
    family: ThemeFamily
    palette_label: str
    colors: ThemeColors
    cyberpunk_intensity: float = Field(ge=0.0, le=1.0)
    visual_density: VisualDensity
    motion: MotionLevel
    icon_style: str
    local_photo_usage: LocalPhotoUsage
    monitor_plan: MonitorThemePlan
    notes: list[str] = Field(default_factory=list)
