"""Wallpaper manifest persistence."""

from __future__ import annotations

import json
from pathlib import Path

from chaseos.models.assets import WallpaperManifest

WALLPAPER_MANIFEST_NAME = "wallpaper_manifest.json"


class WallpaperManifestStore:
    """Save and load daily wallpaper manifests."""

    def save(self, manifest: WallpaperManifest, path: Path) -> WallpaperManifest:
        path.parent.mkdir(parents=True, exist_ok=True)
        manifest.manifest_path = path
        path.write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return manifest

    def load(self, path: Path) -> WallpaperManifest | None:
        if not path.exists():
            return None
        return WallpaperManifest.model_validate_json(path.read_text(encoding="utf-8"))
