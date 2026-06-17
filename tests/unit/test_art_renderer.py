from __future__ import annotations

import inspect

from PIL import Image

from chaseos.models.poster import Display1ArtPlan
from chaseos.models.theme import ThemeFamily
from chaseos.poster.art_renderer import DISPLAY1_ART_SIZE, Display1ArtRenderer


def _plan(seed: int = 1234) -> Display1ArtPlan:
    return Display1ArtPlan(
        family=ThemeFamily.DUSK_SKYLINE,
        motif="dusk_skyline",
        seed=seed,
        public_safe_takeaway="Make repeated work visible.",
        cyberpunk_intensity=0.72,
        show_figure=True,
        show_geometry=True,
        show_scanlines=True,
    )


def test_art_renderer_is_deterministic_for_same_plan(tmp_path) -> None:
    renderer = Display1ArtRenderer()
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"

    renderer.render(_plan(), first, tmp_path / "first.json")
    renderer.render(_plan(), second, tmp_path / "second.json")

    assert first.read_bytes() == second.read_bytes()


def test_art_renderer_outputs_display_one_dimensions(tmp_path) -> None:
    path = tmp_path / "art.png"
    Display1ArtRenderer().render(_plan(), path, tmp_path / "meta.json")

    with Image.open(path) as image:
        assert image.size == DISPLAY1_ART_SIZE == (1080, 1920)


def test_art_renderer_does_not_use_font_or_draw_text() -> None:
    source = inspect.getsource(Display1ArtRenderer)

    assert "ImageFont" not in source
    assert ".text(" not in source
    assert "draw.text" not in source
