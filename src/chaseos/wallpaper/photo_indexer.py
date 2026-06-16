"""Private local photo indexing helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from chaseos.models.assets import PhotoAsset, PhotoIndex, PhotoOrientation
from chaseos.storage.paths import get_photo_index_path
from chaseos.wallpaper.photo_source import PhotoSourceConfig


class PhotoLibraryIndexer:
    """Index private local photos using only local Pillow metadata."""

    def __init__(
        self,
        config: PhotoSourceConfig | None = None,
        base_path: Path | str | None = None,
    ) -> None:
        self.config = config or PhotoSourceConfig()
        self.base_path = Path(base_path) if base_path is not None else None

    @property
    def index_path(self) -> Path:
        return get_photo_index_path(self.base_path)

    def source_exists(self) -> bool:
        return self.config.enabled and self.config.source_path.exists()

    def load(self) -> PhotoIndex | None:
        if not self.index_path.exists():
            return None
        return PhotoIndex.model_validate_json(self.index_path.read_text(encoding="utf-8"))

    def index(self, save: bool = True) -> PhotoIndex:
        indexed_at = datetime.now(UTC)
        source_path = self.config.source_path
        photos: list[PhotoAsset] = []

        if not self.config.enabled or not source_path.exists():
            return PhotoIndex(
                source_path=source_path,
                recursive=self.config.recursive,
                supported_formats=self.config.supported_formats,
                allow_public_use=False,
                indexed_at=indexed_at,
                photo_count=0,
                photos=[],
            )

        for image_path in self._candidate_paths(source_path):
            asset = self._index_one(image_path, indexed_at)
            if asset is not None:
                photos.append(asset)

        photo_index = PhotoIndex(
            source_path=source_path,
            recursive=self.config.recursive,
            supported_formats=self.config.supported_formats,
            allow_public_use=False,
            indexed_at=indexed_at,
            photo_count=len(photos),
            photos=photos,
        )
        if save:
            self.save(photo_index)
        return photo_index

    def save(self, photo_index: PhotoIndex) -> PhotoIndex:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(
            json.dumps(photo_index.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return photo_index

    def _candidate_paths(self, source_path: Path) -> list[Path]:
        supported = {suffix.lower() for suffix in self.config.supported_formats}
        iterator = source_path.rglob("*") if self.config.recursive else source_path.glob("*")
        return sorted(
            path
            for path in iterator
            if path.is_file() and path.suffix.lower() in supported
        )

    def _index_one(self, image_path: Path, indexed_at: datetime) -> PhotoAsset | None:
        try:
            with Image.open(image_path) as image:
                rgb = image.convert("RGB")
                width, height = image.size
                average_color, brightness, saturation = self._image_metrics(rgb)
        except (OSError, UnidentifiedImageError, ValueError):
            return None

        return PhotoAsset(
            path=image_path,
            width=width,
            height=height,
            orientation=self._orientation(width, height),
            average_color=average_color,
            brightness=brightness,
            saturation=saturation,
            file_size_bytes=image_path.stat().st_size,
            indexed_at=indexed_at,
        )

    def _orientation(self, width: int, height: int) -> PhotoOrientation:
        if width > height:
            return PhotoOrientation.LANDSCAPE
        if height > width:
            return PhotoOrientation.PORTRAIT
        return PhotoOrientation.SQUARE

    def _image_metrics(self, image: Image.Image) -> tuple[str, float, float]:
        sample = image.copy()
        sample.thumbnail((32, 32), Image.Resampling.LANCZOS)
        data = sample.tobytes()
        pixels = list(zip(data[0::3], data[1::3], data[2::3], strict=True))
        if not pixels:
            return "#000000", 0.0, 0.0

        total_r = sum(pixel[0] for pixel in pixels)
        total_g = sum(pixel[1] for pixel in pixels)
        total_b = sum(pixel[2] for pixel in pixels)
        count = len(pixels)
        avg_r = round(total_r / count)
        avg_g = round(total_g / count)
        avg_b = round(total_b / count)

        brightness = sum(
            (0.2126 * pixel[0]) + (0.7152 * pixel[1]) + (0.0722 * pixel[2])
            for pixel in pixels
        ) / (255 * count)
        saturation = sum(self._pixel_saturation(pixel) for pixel in pixels) / count

        return (
            f"#{avg_r:02x}{avg_g:02x}{avg_b:02x}",
            round(brightness, 4),
            round(saturation, 4),
        )

    def _pixel_saturation(self, pixel: tuple[int, int, int]) -> float:
        maximum = max(pixel)
        if maximum == 0:
            return 0.0
        return (maximum - min(pixel)) / maximum
