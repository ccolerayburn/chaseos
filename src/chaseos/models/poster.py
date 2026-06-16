"""Public poster models for ChaseOS."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class PublicPosterStyle(StrEnum):
    OBSIDIAN_SIGNAL = "Obsidian Signal"
    NEON_BLUEPRINT = "Neon Blueprint"
    CHROME_MONOLITH = "Chrome Monolith"
    VIOLET_CIRCUIT = "Violet Circuit"
    REDLINE_PROTOCOL = "Redline Protocol"
    ARCTIC_INTERFACE = "Arctic Interface"
    SYNTHETIC_SUNRISE = "Synthetic Sunrise"


class PublicPosterPlan(BaseModel):
    """Public-safe plan for Display 1."""

    display: int = 1
    width: int = 1080
    height: int = 1920
    style_family: PublicPosterStyle
    quote: str
    subtitle: str | None = "Daily Innovation Signal"
    public_safe_takeaway: str
    source_policy: str = "innovation_takeaway_only"
    safe: bool = True
    visual_density: str = "minimal"
    cyberpunk_intensity: float = Field(default=0.45, ge=0.0, le=1.0)
    change_requests: list[str] = Field(default_factory=list)
    regenerate_count: int = 0


class PublicPosterRenderResult(BaseModel):
    """Rendered public poster file information."""

    image_path: Path
    metadata_path: Path
    width: int = 1080
    height: int = 1920


class PublicPosterMetadata(BaseModel):
    """Metadata saved next to the generated public poster."""

    date: date
    generated_at: datetime
    innovation_exercise: str
    private_takeaway: str
    public_safe_takeaway: str
    quote: str
    subtitle: str | None
    style_family: str
    image_path: str
    width: int
    height: int
    approved: bool
    change_requests: list[str]
    regenerate_count: int
    source_policy: str = "innovation_takeaway_only"
    raw_check_in_used_for_content: bool = False
