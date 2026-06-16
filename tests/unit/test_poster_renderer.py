import json

from PIL import Image

from chaseos.models.signals import PracticalSignals, StartupMode
from chaseos.poster.public_poster_engine import PublicPosterEngine
from chaseos.theming.theme_generator import ThemeGenerator


def test_poster_png_and_metadata_are_created(tmp_path) -> None:
    theme = ThemeGenerator().generate(PracticalSignals(), StartupMode.STRUCTURED).plan
    engine = PublicPosterEngine(base_path=tmp_path)
    plan = engine.build_plan(
        innovation_exercise="10% Less Dumb",
        private_innovation_takeaway="We keep asking the same questions manually.",
        theme_plan=theme,
    )

    result = engine.render(
        plan=plan,
        innovation_exercise="10% Less Dumb",
        private_innovation_takeaway="We keep asking the same questions manually.",
        theme_plan=theme,
        approved=True,
    )

    assert result.image_path.exists()
    assert result.metadata_path.exists()


def test_poster_png_is_exactly_1080x1920(tmp_path) -> None:
    theme = ThemeGenerator().generate(PracticalSignals(), StartupMode.STRUCTURED).plan
    engine = PublicPosterEngine(base_path=tmp_path)
    plan = engine.build_plan(
        innovation_exercise="10% Less Dumb",
        private_innovation_takeaway="Better inputs make faster fixes.",
        theme_plan=theme,
    )
    result = engine.render(
        plan=plan,
        innovation_exercise="10% Less Dumb",
        private_innovation_takeaway="Better inputs make faster fixes.",
        theme_plan=theme,
        approved=True,
    )

    with Image.open(result.image_path) as image:
        assert image.size == (1080, 1920)


def test_metadata_width_height_match(tmp_path) -> None:
    theme = ThemeGenerator().generate(PracticalSignals(), StartupMode.STRUCTURED).plan
    engine = PublicPosterEngine(base_path=tmp_path)
    plan = engine.build_plan(
        innovation_exercise="10% Less Dumb",
        private_innovation_takeaway="Clear handoffs reduce repeated work.",
        theme_plan=theme,
    )
    result = engine.render(
        plan=plan,
        innovation_exercise="10% Less Dumb",
        private_innovation_takeaway="Clear handoffs reduce repeated work.",
        theme_plan=theme,
        approved=True,
    )

    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata["width"] == 1080
    assert metadata["height"] == 1920


def test_rendering_works_with_temp_directory(tmp_path) -> None:
    engine = PublicPosterEngine(base_path=tmp_path)
    plan = engine.build_plan(
        innovation_exercise="10% Less Dumb",
        private_innovation_takeaway="Turn friction into a system.",
        theme_plan=None,
    )

    result = engine.render(
        plan=plan,
        innovation_exercise="10% Less Dumb",
        private_innovation_takeaway="Turn friction into a system.",
        theme_plan=None,
        approved=True,
    )

    assert tmp_path in result.image_path.parents
