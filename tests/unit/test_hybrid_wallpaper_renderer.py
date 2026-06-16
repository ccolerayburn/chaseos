from PIL import Image

from chaseos.models.signals import PracticalSignals, StartupMode
from chaseos.theming.theme_generator import ThemeGenerator
from chaseos.wallpaper.wallpaper_renderer import (
    DEFAULT_WALLPAPER_SIZE,
    WallpaperRenderer,
    WallpaperRenderSpec,
)


def theme_plan():
    return ThemeGenerator().generate(PracticalSignals(), StartupMode.STRUCTURED).plan


def test_hybrid_renderer_outputs_exact_landscape_png_without_exif(tmp_path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (2600, 1400), (180, 120, 50)).save(source)
    output = tmp_path / "display_4_left_atmosphere.png"

    wallpaper = WallpaperRenderer().render(
        WallpaperRenderSpec(
            display_id=4,
            role="left_atmosphere",
            style="atmosphere_gradient",
            width=1920,
            height=1080,
            output_path=output,
            seed=42,
            photo_path=source,
            photo_mode="hybrid",
        ),
        theme_plan(),
    )

    assert wallpaper.image_path.exists()
    assert wallpaper.selected_photo_path == source
    assert wallpaper.generation_mode == "hybrid"
    with Image.open(output) as image:
        assert image.size == DEFAULT_WALLPAPER_SIZE
        assert image.format == "PNG"
        assert "exif" not in image.info


def test_hybrid_renderer_falls_back_when_photo_path_is_missing(tmp_path) -> None:
    output = tmp_path / "display_4_left_atmosphere.png"

    wallpaper = WallpaperRenderer().render(
        WallpaperRenderSpec(
            display_id=4,
            role="left_atmosphere",
            style="atmosphere_gradient",
            width=1920,
            height=1080,
            output_path=output,
            seed=42,
            photo_path=tmp_path / "missing.jpg",
            photo_mode="hybrid",
        ),
        theme_plan(),
    )

    assert output.exists()
    assert wallpaper.selected_photo_path is None
    assert wallpaper.generation_mode == "atmosphere_gradient"
    assert wallpaper.fallback_reason is not None


def test_center_command_generated_wallpaper_has_lowest_visual_noise(tmp_path) -> None:
    renderer = WallpaperRenderer()
    plan = theme_plan()
    center = renderer.render(
        WallpaperRenderSpec(
            display_id=2,
            role="center_command",
            style="command_grid",
            width=1920,
            height=1080,
            output_path=tmp_path / "center.png",
            seed=1,
        ),
        plan,
    )
    left = renderer.render(
        WallpaperRenderSpec(
            display_id=4,
            role="left_atmosphere",
            style="atmosphere_gradient",
            width=1920,
            height=1080,
            output_path=tmp_path / "left.png",
            seed=1,
        ),
        plan,
    )

    assert center.visual_noise_score < left.visual_noise_score
