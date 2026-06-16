from pathlib import Path

from PIL import Image

from chaseos.models.assets import PhotoOrientation
from chaseos.wallpaper.photo_indexer import PhotoLibraryIndexer
from chaseos.wallpaper.photo_source import PhotoSourceConfig


def make_image(path: Path, size: tuple[int, int], color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)


def test_photo_indexer_handles_missing_source_gracefully(tmp_path) -> None:
    config = PhotoSourceConfig(source_path=tmp_path / "missing")
    indexer = PhotoLibraryIndexer(config=config, base_path=tmp_path / "data")

    photo_index = indexer.index()

    assert photo_index.photo_count == 0
    assert photo_index.photos == []
    assert photo_index.allow_public_use is False
    assert indexer.load() is None


def test_photo_indexer_indexes_supported_images_and_saves_json(tmp_path) -> None:
    source = tmp_path / "photos"
    make_image(source / "landscape.jpg", (1200, 800), (200, 140, 40))
    make_image(source / "nested" / "portrait.png", (800, 1200), (40, 100, 180))
    make_image(source / "ignored.bmp", (200, 200), (255, 0, 0))
    (source / "corrupt.jpg").write_text("not an image", encoding="utf-8")
    (source / "notes.txt").write_text("private notes", encoding="utf-8")

    config = PhotoSourceConfig(source_path=source)
    indexer = PhotoLibraryIndexer(config=config, base_path=tmp_path / "data")

    photo_index = indexer.index()
    loaded = indexer.load()

    assert photo_index.photo_count == 2
    assert loaded is not None
    assert loaded.photo_count == 2
    assert loaded.allow_public_use is False
    assert indexer.index_path.exists()
    assert {photo.orientation for photo in loaded.photos} == {
        PhotoOrientation.LANDSCAPE,
        PhotoOrientation.PORTRAIT,
    }
    for photo in loaded.photos:
        assert photo.width > 0
        assert photo.height > 0
        assert photo.average_color.startswith("#")
        assert 0.0 <= photo.brightness <= 1.0
        assert 0.0 <= photo.saturation <= 1.0
        assert photo.file_size_bytes > 0
        assert photo.indexed_at is not None


def test_photo_indexer_honors_non_recursive_config(tmp_path) -> None:
    source = tmp_path / "photos"
    make_image(source / "root.jpg", (1200, 800), (200, 140, 40))
    make_image(source / "nested" / "nested.jpg", (1200, 800), (40, 100, 180))

    config = PhotoSourceConfig(source_path=source, recursive=False)
    indexer = PhotoLibraryIndexer(config=config, base_path=tmp_path / "data")

    photo_index = indexer.index()

    assert photo_index.photo_count == 1
    assert photo_index.photos[0].path.name == "root.jpg"
