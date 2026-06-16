from datetime import date

from PIL import Image

from chaseos.models.signals import PracticalSignals, StartupMode
from chaseos.theming.theme_generator import ThemeGenerator
from chaseos.wallpaper.photo_source import PhotoSourceConfig
from chaseos.wallpaper.wallpaper_composer import WallpaperComposer
from chaseos.wallpaper.wallpaper_renderer import DEFAULT_WALLPAPER_SIZE, WALLPAPER_ROLES
from chaseos.windows.display_detection import KNOWN_DISPLAY_ROLES


def test_private_wallpaper_roles_match_known_displays() -> None:
    assert KNOWN_DISPLAY_ROLES[4] == "left_atmosphere"
    assert KNOWN_DISPLAY_ROLES[2] == "center_command"
    assert KNOWN_DISPLAY_ROLES[3] == "right_inspiration"
    assert set(WALLPAPER_ROLES) == {
        "public_signal",
        "left_atmosphere",
        "center_command",
        "right_inspiration",
    }


def theme_plan():
    return ThemeGenerator().generate(PracticalSignals(), StartupMode.STRUCTURED).plan


def composer(tmp_path):
    return WallpaperComposer(
        base_path=tmp_path,
        photo_config=PhotoSourceConfig(source_path=tmp_path / "missing_photos"),
    )


def test_wallpaper_composer_generates_all_four_wallpapers(tmp_path) -> None:
    manifest = composer(tmp_path).generate(
        theme_plan=theme_plan(),
        run_date=date(2026, 6, 15),
    )

    assert set(manifest.wallpapers) == {"display_1", "display_4", "display_2", "display_3"}
    assert manifest.wallpapers["display_1"].image_path.exists()
    assert manifest.wallpapers["display_4"].image_path.exists()
    assert manifest.wallpapers["display_2"].image_path.exists()
    assert manifest.wallpapers["display_3"].image_path.exists()


def test_display_one_placeholder_public_signal_is_1080x1920(tmp_path) -> None:
    manifest = composer(tmp_path).generate(
        theme_plan=theme_plan(),
        run_date=date(2026, 6, 15),
    )

    with Image.open(manifest.wallpapers["display_1"].image_path) as image:
        assert image.size == (1080, 1920)
        assert image.format == "PNG"


def test_landscape_wallpaper_images_are_exactly_1920x1080_by_default(tmp_path) -> None:
    manifest = composer(tmp_path).generate(
        theme_plan=theme_plan(),
        run_date=date(2026, 6, 15),
    )

    for display_key in ("display_4", "display_2", "display_3"):
        with Image.open(manifest.wallpapers[display_key].image_path) as image:
            assert image.size == DEFAULT_WALLPAPER_SIZE
            assert image.format == "PNG"


def test_display_two_uses_center_command_style(tmp_path) -> None:
    manifest = composer(tmp_path).generate(
        theme_plan=theme_plan(),
        run_date=date(2026, 6, 15),
    )

    assert manifest.wallpapers["display_2"].role == "center_command"
    assert manifest.wallpapers["display_2"].generation_mode == "command_grid"


def test_wallpaper_manifest_is_saved_with_theme_and_policy(tmp_path) -> None:
    manifest = composer(tmp_path).generate(
        theme_plan=theme_plan(),
        run_date=date(2026, 6, 15),
    )

    assert manifest.manifest_path is not None
    assert manifest.manifest_path.exists()
    assert manifest.theme_family
    assert manifest.startup_mode == "Structured Start"
    assert manifest.source_policy.applied_to_windows is False
    assert manifest.monitor_mapping_source in {"fallback", "saved"}
    assert manifest.role_mapping["public_signal"] == "display 1"
    assert manifest.role_mapping["left_atmosphere"] == "display 4"
    assert manifest.role_mapping["center_command"] == "display 2"
    assert manifest.role_mapping["right_inspiration"] == "display 3"


def test_wallpaper_manifest_does_not_include_private_text(tmp_path) -> None:
    manifest = composer(tmp_path).generate(
        theme_plan=theme_plan(),
        run_date=date(2026, 6, 15),
    )
    manifest_text = manifest.manifest_path.read_text(encoding="utf-8")

    assert "slept bad" not in manifest_text
    assert "we keep repeating" not in manifest_text


def test_private_wallpaper_images_are_distinct(tmp_path) -> None:
    manifest = composer(tmp_path).generate(
        theme_plan=theme_plan(),
        run_date=date(2026, 6, 15),
    )

    image_bytes = {
        key: wallpaper.image_path.read_bytes() for key, wallpaper in manifest.wallpapers.items()
    }
    assert image_bytes["display_4"] != image_bytes["display_2"]
    assert image_bytes["display_2"] != image_bytes["display_3"]


def test_composer_can_generate_to_direct_output_folder(tmp_path) -> None:
    output_folder = tmp_path / "wallpapers"
    manifest = WallpaperComposer(
        photo_config=PhotoSourceConfig(source_path=tmp_path / "missing_photos"),
    ).generate(
        theme_plan=theme_plan(),
        run_date=date(2026, 6, 15),
        output_folder=output_folder,
    )

    assert manifest.manifest_path == output_folder / "wallpaper_manifest.json"
    assert (
        manifest.wallpapers["display_1"].image_path
        == output_folder / "display_1_public_signal.png"
    )


def test_daily_seed_is_stable_for_same_date_and_theme(tmp_path) -> None:
    composer = WallpaperComposer(
        base_path=tmp_path,
        photo_config=PhotoSourceConfig(source_path=tmp_path / "missing_photos"),
    )
    plan = theme_plan()

    first = composer.daily_seed(date(2026, 6, 15), plan, "center_command")
    second = composer.daily_seed(date(2026, 6, 15), plan, "center_command")

    assert first == second


def test_different_dates_produce_different_output_paths_or_metadata(tmp_path) -> None:
    composer = WallpaperComposer(
        base_path=tmp_path,
        photo_config=PhotoSourceConfig(source_path=tmp_path / "missing_photos"),
    )
    first = composer.generate(theme_plan=theme_plan(), run_date=date(2026, 6, 15))
    second = composer.generate(theme_plan=theme_plan(), run_date=date(2026, 6, 16))

    assert first.manifest_path != second.manifest_path
