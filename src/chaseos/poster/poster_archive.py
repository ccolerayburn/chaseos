"""Public poster archive helpers."""

from __future__ import annotations

import json
from pathlib import Path

from chaseos.models.poster import Display1ArtMetadata, PublicPosterMetadata

POSTER_IMAGE_NAME = "display_1_public_signal.png"
POSTER_METADATA_NAME = "public_poster_meta.json"


class PosterArchive:
    """Save and load public poster metadata."""

    def save_metadata(
        self,
        metadata: PublicPosterMetadata | Display1ArtMetadata,
        metadata_path: Path,
    ) -> None:
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(
            json.dumps(metadata.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

    def load_metadata(
        self, metadata_path: Path
    ) -> PublicPosterMetadata | Display1ArtMetadata | None:
        if not metadata_path.exists():
            return None
        raw = metadata_path.read_text(encoding="utf-8")
        try:
            return PublicPosterMetadata.model_validate_json(raw)
        except ValueError:
            return Display1ArtMetadata.model_validate_json(raw)
