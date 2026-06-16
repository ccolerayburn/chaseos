"""Local photo source configuration."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

LOCAL_PHOTO_SOURCE = r"C:\_Media\Photos\Lightroom\Export"
SUPPORTED_PHOTO_FORMATS = (".jpg", ".jpeg", ".png", ".webp")


class PhotoSourceConfig(BaseModel):
    """Configuration for the private local photo library."""

    source_path: Path = Path(LOCAL_PHOTO_SOURCE)
    recursive: bool = True
    supported_formats: tuple[str, ...] = SUPPORTED_PHOTO_FORMATS
    allow_public_use: bool = False
    enabled: bool = True
    avoid_repeats_days: int = Field(default=30, ge=0)
