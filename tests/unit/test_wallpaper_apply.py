from __future__ import annotations

import json
import platform
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from chaseos.models.assets import GeneratedWallpaper, WallpaperManifest
from chaseos.models.monitor import MonitorRole
from chaseos.ritual.startup_sequence import StartupSequence
from chaseos.storage.paths import get_last_apply_manifest_path, get_previous_wallpapers_path
from chaseos.wallpaper.applier import WallpaperApplier
from chaseos.wallpaper.photo_source import PhotoSourceConfig
from chaseos.wallpaper.plan import WallpaperApplyPlanner, WallpaperPlanError
from chaseos.wallpaper.rollback import WallpaperRollbackStore
from chaseos.wallpaper.wallpaper_manifest import WALLPAPER_MANIFEST_NAME, WallpaperManifestStore
from chaseos.wallpaper.windows_desktop_wallpaper import (
    DesktopWallpaperError,
    WindowsDesktopWallpaper,
)
from chaseos.windows.display_detection import get_fallback_monitor_layout


class FakeDesktopWallpaper:
    def __init__(
        self,
        previous: dict[str, Path] | None = None,
        rollback_path: Path | None = None,
    ) -> None:
        self.previous = previous or {}
        self.rollback_path = rollback_path
        self.set_calls: list[tuple[str, str]] = []
        self.rollback_existed_before_first_set: bool | None = None

    def list_monitors(self) -> tuple[str, ...]:
        return tuple(self.previous)

    def get_wallpaper(self, monitor_id: str) -> str | None:
        path = self.previous.get(monitor_id)
        return str(path) if path is not None else None

    def set_wallpaper(self, monitor_id: str, image_path: str) -> None:
        if self.rollback_existed_before_first_set is None and self.rollback_path is not None:
            self.rollback_existed_before_first_set = self.rollback_path.exists()
        self.set_calls.append((monitor_id, image_path))


def render_response_text(response) -> str:
    return "\n".join(line.render() for line in response.lines)


def write_file(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("image placeholder", encoding="utf-8")
    return path


def generated_wallpaper(display_id: int, role: str, image_path: Path) -> GeneratedWallpaper:
    return GeneratedWallpaper(
        display_id=display_id,
        role=role,
        width=1080 if display_id == 1 else 1920,
        height=1920 if display_id == 1 else 1080,
        image_path=image_path,
        generation_mode="generated",
        theme_family="Obsidian Terminal",
        created_at=datetime.now(UTC),
        public_safe=display_id == 1,
    )


def write_manifest(
    tmp_path: Path,
    *,
    public_path: Path | None = None,
    omit_display: str | None = None,
) -> WallpaperManifest:
    run_date = date(2026, 6, 16)
    generated_dir = tmp_path / "generated" / run_date.isoformat()
    paths = {
        "display_1": public_path or write_file(generated_dir / "display_1_public_signal.png"),
        "display_4": write_file(generated_dir / "display_4_left_atmosphere.png"),
        "display_2": write_file(generated_dir / "display_2_center_command.png"),
        "display_3": write_file(generated_dir / "display_3_right_inspiration.png"),
    }
    roles = {
        "display_1": "public_signal",
        "display_4": "left_atmosphere",
        "display_2": "center_command",
        "display_3": "right_inspiration",
    }
    display_ids = {
        "display_1": 1,
        "display_4": 4,
        "display_2": 2,
        "display_3": 3,
    }
    wallpapers = {
        key: generated_wallpaper(display_ids[key], roles[key], path)
        for key, path in paths.items()
        if key != omit_display
    }
    manifest = WallpaperManifest(
        date=run_date,
        generated_at=datetime.now(UTC),
        theme_family="Obsidian Terminal",
        startup_mode="Structured Start",
        wallpapers=wallpapers,
        public_poster_path=paths["display_1"],
        public_poster_included=True,
    )
    return WallpaperManifestStore().save(manifest, generated_dir / WALLPAPER_MANIFEST_NAME)


def build_plan(tmp_path: Path):
    return WallpaperApplyPlanner(base_path=tmp_path).build_plan(get_fallback_monitor_layout())


def test_apply_wallpapers_defaults_to_dry_run(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("chaseos.windows.display_detection.detect_monitors", lambda: [])
    write_manifest(tmp_path)
    fake = FakeDesktopWallpaper()
    sequence = StartupSequence(
        data_dir=tmp_path,
        wallpaper_applier=WallpaperApplier(client=fake, base_path=tmp_path),
    )

    response = sequence.handle_input("/apply wallpapers")

    assert "CHASEOS // WALLPAPER APPLY DRY RUN" in render_response_text(response)
    assert "No changes applied." in render_response_text(response)
    assert fake.set_calls == []


def test_apply_wallpapers_dry_run_applies_nothing(tmp_path) -> None:
    write_manifest(tmp_path)
    fake = FakeDesktopWallpaper()
    plan = build_plan(tmp_path)

    lines = WallpaperApplier(client=fake, base_path=tmp_path).dry_run(plan)

    assert any("DRY RUN" in line for line in lines)
    assert fake.set_calls == []


def test_apply_wallpapers_confirm_saves_rollback_before_setting(tmp_path) -> None:
    write_manifest(tmp_path)
    previous = write_file(tmp_path / "previous" / "old.png")
    fake = FakeDesktopWallpaper(
        previous={target.monitor_id: previous for target in build_plan(tmp_path).targets},
        rollback_path=get_previous_wallpapers_path(tmp_path),
    )

    WallpaperApplier(client=fake, base_path=tmp_path).apply_confirmed(build_plan(tmp_path))

    assert fake.rollback_existed_before_first_set is True
    assert get_previous_wallpapers_path(tmp_path).exists()


def test_apply_wallpapers_confirm_applies_all_four_roles(tmp_path) -> None:
    write_manifest(tmp_path)
    fake = FakeDesktopWallpaper()

    WallpaperApplier(client=fake, base_path=tmp_path).apply_confirmed(build_plan(tmp_path))

    assert len(fake.set_calls) == 4
    assert {monitor_id for monitor_id, _path in fake.set_calls} == {
        "fallback_display_1",
        "fallback_display_4",
        "fallback_display_2",
        "fallback_display_3",
    }


def test_public_role_rejects_lightroom_or_general_photo_paths(tmp_path) -> None:
    public_photo = write_file(tmp_path / "photos" / "export" / "public.jpg")
    write_manifest(tmp_path, public_path=public_photo)
    planner = WallpaperApplyPlanner(
        base_path=tmp_path,
        photo_config=PhotoSourceConfig(source_path=tmp_path / "photos" / "export"),
    )

    with pytest.raises(WallpaperPlanError, match="public role rejected"):
        planner.build_plan(get_fallback_monitor_layout())


def test_missing_required_role_fails(tmp_path) -> None:
    write_manifest(tmp_path)
    layout = get_fallback_monitor_layout()
    del layout.assignments[MonitorRole.RIGHT_INSPIRATION]

    with pytest.raises(WallpaperPlanError, match="missing required role: right"):
        WallpaperApplyPlanner(base_path=tmp_path).build_plan(layout)


def test_missing_image_path_fails(tmp_path) -> None:
    manifest = write_manifest(tmp_path)
    manifest.wallpapers["display_2"].image_path.unlink()

    with pytest.raises(WallpaperPlanError, match="missing image path"):
        build_plan(tmp_path)


def test_reset_wallpapers_restores_previous_paths(tmp_path) -> None:
    previous = write_file(tmp_path / "previous" / "old.png")
    WallpaperRollbackStore(base_path=tmp_path).save({"monitor-a": previous})
    fake = FakeDesktopWallpaper()

    lines = WallpaperApplier(client=fake, base_path=tmp_path).reset()

    assert fake.set_calls == [("monitor-a", str(previous))]
    assert any("Restored wallpapers: 1" in line for line in lines)


def test_reset_wallpapers_skips_missing_previous_files(tmp_path) -> None:
    missing = tmp_path / "previous" / "missing.png"
    WallpaperRollbackStore(base_path=tmp_path).save({"monitor-a": missing})
    fake = FakeDesktopWallpaper()

    lines = WallpaperApplier(client=fake, base_path=tmp_path).reset()

    assert fake.set_calls == []
    assert any("Skipped missing previous wallpaper" in line for line in lines)


def test_non_windows_wrapper_fails_gracefully(monkeypatch) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Linux")

    with pytest.raises(DesktopWallpaperError, match="only available on Windows"):
        WindowsDesktopWallpaper()


def test_apply_manifest_is_written_after_confirm(tmp_path) -> None:
    write_manifest(tmp_path)
    fake = FakeDesktopWallpaper()

    WallpaperApplier(client=fake, base_path=tmp_path).apply_confirmed(build_plan(tmp_path))

    manifest_path = get_last_apply_manifest_path(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_path.exists()
    assert payload["generated_date"] == "2026-06-16"
    assert len(payload["targets"]) == 4


def test_reset_wallpapers_command_uses_rollback(tmp_path) -> None:
    previous = write_file(tmp_path / "previous" / "old.png")
    WallpaperRollbackStore(base_path=tmp_path).save({"monitor-a": previous})
    fake = FakeDesktopWallpaper()
    sequence = StartupSequence(
        data_dir=tmp_path,
        wallpaper_applier=WallpaperApplier(client=fake, base_path=tmp_path),
    )

    response = sequence.handle_input("/reset wallpapers")

    assert "CHASEOS // WALLPAPER RESET" in render_response_text(response)
    assert fake.set_calls == [("monitor-a", str(previous))]
