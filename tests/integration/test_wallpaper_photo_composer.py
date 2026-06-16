import json
from datetime import date

from PIL import Image

from chaseos.models.signals import EnergyLevel, PracticalSignals, StartupMode
from chaseos.models.theme import LocalPhotoUsage, PhotoUsage
from chaseos.theming.theme_generator import ThemeGenerator
from chaseos.wallpaper.photo_indexer import PhotoLibraryIndexer
from chaseos.wallpaper.photo_source import PhotoSourceConfig
from chaseos.wallpaper.wallpaper_composer import WallpaperComposer


def make_image(path, size=(2400, 1400), color=(180, 120, 50)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)


def photo_theme_plan(change_requests: list[str] | None = None):
    return ThemeGenerator().generate(
        PracticalSignals(energy=EnergyLevel.HIGH),
        StartupMode.MOMENTUM,
        change_requests=change_requests or ["use more local photos"],
    ).plan


def test_composer_uses_photo_index_for_private_hybrid_wallpapers(tmp_path) -> None:
    source = tmp_path / "photos"
    make_image(source / "landscape.jpg")
    config = PhotoSourceConfig(source_path=source)
    photo_index = PhotoLibraryIndexer(config=config, base_path=tmp_path / "data").index()

    manifest = WallpaperComposer(base_path=tmp_path / "data", photo_config=config).generate(
        theme_plan=photo_theme_plan(),
        run_date=date(2026, 6, 15),
        photo_index=photo_index,
    )

    assert manifest.photo_index_used is True
    assert manifest.public_monitor_uses_general_photos is False
    assert manifest.private_selected_photos["display_4"].selected_photo_path is not None
    assert manifest.private_selected_photos["display_3"].selected_photo_path is not None
    assert manifest.wallpapers["display_4"].selected_photo_path is not None
    assert manifest.wallpapers["display_3"].selected_photo_path is not None
    assert manifest.wallpapers["display_2"].selected_photo_path is None
    assert manifest.wallpapers["display_2"].generation_mode == "command_grid"


def test_composer_falls_back_to_generated_when_photo_index_is_empty(tmp_path) -> None:
    plan = photo_theme_plan().model_copy(
        update={"local_photo_usage": LocalPhotoUsage(display_4=PhotoUsage.HYBRID)}
    )

    manifest = WallpaperComposer(
        base_path=tmp_path,
        photo_config=PhotoSourceConfig(source_path=tmp_path / "missing_photos"),
    ).generate(
        theme_plan=plan,
        run_date=date(2026, 6, 15),
        photo_index=None,
        use_photo_index=False,
    )

    assert manifest.photo_index_used is False
    assert manifest.private_selected_photos["display_4"].fallback_used is True
    assert manifest.wallpapers["display_4"].selected_photo_path is None
    assert manifest.fallback_reasons["display_4"] == "no valid local photos available"


def test_composer_preserves_approved_display_one_poster_path(tmp_path) -> None:
    poster_path = tmp_path / "posters" / "display_1_public_signal.png"
    make_image(poster_path, size=(1080, 1920), color=(20, 20, 20))

    manifest = WallpaperComposer(
        base_path=tmp_path / "data",
        photo_config=PhotoSourceConfig(source_path=tmp_path / "missing_photos"),
    ).generate(
        theme_plan=photo_theme_plan(["no photos today"]),
        run_date=date(2026, 6, 15),
        public_poster_path=poster_path,
    )

    assert manifest.public_poster_path == poster_path
    assert manifest.display_1_source == "approved_public_poster"
    assert "display_1" not in manifest.wallpapers
    assert manifest.public_monitor_uses_general_photos is False


def test_composer_uses_placeholder_display_one_only_without_approved_poster(tmp_path) -> None:
    manifest = WallpaperComposer(
        base_path=tmp_path,
        photo_config=PhotoSourceConfig(source_path=tmp_path / "missing_photos"),
    ).generate(
        theme_plan=photo_theme_plan(["no photos today"]),
        run_date=date(2026, 6, 15),
    )

    assert manifest.display_1_source == "placeholder_public_signal"
    assert manifest.wallpapers["display_1"].image_path.exists()
    with Image.open(manifest.wallpapers["display_1"].image_path) as image:
        assert image.size == (1080, 1920)


def test_composer_manifest_keeps_public_photo_use_disabled_and_contains_no_private_text(
    tmp_path,
) -> None:
    manifest = WallpaperComposer(
        base_path=tmp_path,
        photo_config=PhotoSourceConfig(source_path=tmp_path / "missing_photos"),
    ).generate(
        theme_plan=photo_theme_plan(["no photos today"]),
        run_date=date(2026, 6, 15),
    )

    manifest_json = json.loads(manifest.manifest_path.read_text(encoding="utf-8"))

    assert manifest_json["public_monitor_uses_general_photos"] is False
    assert "slept bad" not in json.dumps(manifest_json)
    assert "VPN tickets keep missing hostname" not in json.dumps(manifest_json)
