"""Generated asset and local photo models."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class PhotoOrientation(StrEnum):
    """Simple image orientation labels used for local selection."""

    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"
    SQUARE = "square"


class PhotoAsset(BaseModel):
    """Private metadata for one locally indexed photo."""

    path: Path
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    orientation: PhotoOrientation
    average_color: str = "#000000"
    brightness: float = Field(ge=0.0, le=1.0)
    saturation: float = Field(ge=0.0, le=1.0)
    file_size_bytes: int = Field(ge=0)
    indexed_at: datetime
    last_used_date: date | None = None
    source_name: str = "lightroom_export"


class PhotoIndex(BaseModel):
    """Private index of local photos available for private monitor wallpapers."""

    source_path: Path
    recursive: bool = True
    supported_formats: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".webp")
    allow_public_use: bool = False
    indexed_at: datetime
    photo_count: int = 0
    photos: list[PhotoAsset] = Field(default_factory=list)


class PhotoSelection(BaseModel):
    """Private selected-photo metadata for one display."""

    display_id: int
    display_key: str
    role: str
    mode: str = "generated"
    selected_photo_path: Path | None = None
    selection_reason: str = ""
    fallback_used: bool = False
    fallback_reason: str | None = None


class GeneratedWallpaper(BaseModel):
    """A locally generated private monitor wallpaper."""

    display_id: int
    role: str
    width: int
    height: int
    image_path: Path
    generation_mode: str
    theme_family: str
    created_at: datetime
    public_safe: bool = False
    source: str = "local_theme_geometry"
    visual_noise_score: float = Field(default=0.0, ge=0.0, le=1.0)
    selected_photo_path: Path | None = None
    fallback_reason: str | None = None


class WallpaperSourcePolicy(BaseModel):
    """Privacy policy embedded in wallpaper manifests."""

    private_wallpapers_use_checkin_text: bool = False
    private_wallpapers_use_public_takeaway: bool = False
    generated_locally: bool = True
    applied_to_windows: bool = False


class WallpaperManifest(BaseModel):
    """Daily private wallpaper manifest."""

    date: date
    generated_at: datetime
    theme_family: str
    startup_mode: str
    wallpapers: dict[str, GeneratedWallpaper]
    public_poster_path: Path | None = None
    public_poster_included: bool = False
    source_policy: WallpaperSourcePolicy = Field(default_factory=WallpaperSourcePolicy)
    photo_index_used: bool = False
    private_selected_photos: dict[str, PhotoSelection] = Field(default_factory=dict)
    fallback_reasons: dict[str, str] = Field(default_factory=dict)
    public_monitor_uses_general_photos: bool = False
    display_1_source: str = "placeholder_public_signal"
    monitor_mapping_source: str = "unknown"
    role_mapping: dict[str, str] = Field(default_factory=dict)
    manifest_path: Path | None = None
