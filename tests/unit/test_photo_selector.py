from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from chaseos.models.assets import PhotoAsset, PhotoIndex, PhotoOrientation
from chaseos.models.signals import EnergyLevel, PracticalSignals, StartupMode
from chaseos.models.theme import LocalPhotoUsage, PhotoUsage
from chaseos.theming.theme_generator import ThemeGenerator
from chaseos.wallpaper.photo_selector import PhotoSelector
from chaseos.wallpaper.photo_source import PhotoSourceConfig


def theme_plan(change_requests: list[str] | None = None):
    return ThemeGenerator().generate(
        PracticalSignals(energy=EnergyLevel.HIGH),
        StartupMode.MOMENTUM,
        change_requests=change_requests,
    ).plan


def asset(
    path: Path,
    *,
    width: int = 1600,
    height: int = 900,
    average_color: str = "#c6a452",
    last_used_date: date | None = None,
) -> PhotoAsset:
    orientation = (
        PhotoOrientation.LANDSCAPE
        if width > height
        else PhotoOrientation.PORTRAIT
        if height > width
        else PhotoOrientation.SQUARE
    )
    return PhotoAsset(
        path=path,
        width=width,
        height=height,
        orientation=orientation,
        average_color=average_color,
        brightness=0.45,
        saturation=0.35,
        file_size_bytes=1000,
        indexed_at=datetime.now(UTC),
        last_used_date=last_used_date,
    )


def photo_index(photos: list[PhotoAsset], source: Path) -> PhotoIndex:
    return PhotoIndex(
        source_path=source,
        indexed_at=datetime.now(UTC),
        photo_count=len(photos),
        photos=photos,
    )


def test_photo_selector_never_returns_display_one(tmp_path) -> None:
    plan = theme_plan(["use more local photos"])
    index = photo_index([asset(tmp_path / "landscape.jpg")], tmp_path)

    selections = PhotoSelector().select_for_private_displays(index, plan)

    assert set(selections) == {"display_4", "display_2", "display_3"}
    assert "display_1" not in selections


def test_photo_selector_prefers_landscape_for_private_displays(tmp_path) -> None:
    plan = theme_plan().model_copy(
        update={"local_photo_usage": LocalPhotoUsage(display_4=PhotoUsage.HYBRID)}
    )
    index = photo_index(
        [
            asset(tmp_path / "portrait.jpg", width=800, height=1200),
            asset(tmp_path / "landscape.jpg", width=1800, height=1000),
        ],
        tmp_path,
    )

    selections = PhotoSelector().select_for_private_displays(index, plan)

    assert selections["display_4"].selected_photo_path == tmp_path / "landscape.jpg"


def test_photo_selector_avoids_recently_used_photos_when_possible(tmp_path) -> None:
    today = date(2026, 6, 15)
    plan = theme_plan().model_copy(
        update={"local_photo_usage": LocalPhotoUsage(display_4=PhotoUsage.HYBRID)}
    )
    index = photo_index(
        [
            asset(tmp_path / "recent.jpg", last_used_date=today - timedelta(days=2)),
            asset(tmp_path / "unused.jpg", last_used_date=None),
        ],
        tmp_path,
    )
    selector = PhotoSelector(PhotoSourceConfig(source_path=tmp_path, avoid_repeats_days=30))

    selections = selector.select_for_private_displays(index, plan, today=today)

    assert selections["display_4"].selected_photo_path == tmp_path / "unused.jpg"


def test_photo_selector_falls_back_when_no_valid_photos_exist(tmp_path) -> None:
    plan = theme_plan().model_copy(
        update={"local_photo_usage": LocalPhotoUsage(display_4=PhotoUsage.HYBRID)}
    )
    index = photo_index([], tmp_path)

    selections = PhotoSelector().select_for_private_displays(index, plan)

    assert selections["display_4"].selected_photo_path is None
    assert selections["display_4"].fallback_used is True
    assert selections["display_4"].fallback_reason == "no valid local photos available"


def test_photo_selector_honors_generated_only_theme_plan(tmp_path) -> None:
    plan = theme_plan(["no photos today"])
    index = photo_index([asset(tmp_path / "landscape.jpg")], tmp_path)

    selections = PhotoSelector().select_for_private_displays(index, plan)

    assert all(selection.selected_photo_path is None for selection in selections.values())
    assert all(selection.mode == PhotoUsage.GENERATED.value for selection in selections.values())


def test_photo_selector_honors_more_local_photos_for_displays_four_and_three(tmp_path) -> None:
    plan = theme_plan(["use more local photos"])
    index = photo_index([asset(tmp_path / "landscape.jpg")], tmp_path)

    selections = PhotoSelector().select_for_private_displays(index, plan)

    assert selections["display_4"].selected_photo_path == tmp_path / "landscape.jpg"
    assert selections["display_3"].selected_photo_path == tmp_path / "landscape.jpg"
    assert selections["display_2"].selected_photo_path is None
    assert selections["display_2"].mode == PhotoUsage.GENERATED.value
