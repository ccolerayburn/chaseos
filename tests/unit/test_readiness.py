from __future__ import annotations

from datetime import UTC, date, datetime
from io import StringIO
from pathlib import Path

from PIL import Image

from chaseos.app.headless import EXIT_SUCCESS, run_headless_cli
from chaseos.app.readiness import ReadinessService
from chaseos.models.assets import GeneratedWallpaper, WallpaperManifest
from chaseos.ritual.startup_sequence import StartupSequence
from chaseos.wallpaper.photo_source import PhotoSourceConfig
from chaseos.wallpaper.wallpaper_manifest import WALLPAPER_MANIFEST_NAME, WallpaperManifestStore


def render_response_text(response) -> str:
    return "\n".join(line.render() for line in response.lines)


def write_image(path: Path, size: tuple[int, int]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (20, 20, 20)).save(path)
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


def write_manifest(tmp_path: Path, public_path: Path | None = None) -> WallpaperManifest:
    run_date = date(2026, 6, 16)
    output_dir = tmp_path / "generated" / run_date.isoformat()
    display_1 = public_path or write_image(output_dir / "display_1_public_signal.png", (1080, 1920))
    display_4 = write_image(output_dir / "display_4_left_atmosphere.png", (1920, 1080))
    display_2 = write_image(output_dir / "display_2_center_command.png", (1920, 1080))
    display_3 = write_image(output_dir / "display_3_right_inspiration.png", (1920, 1080))
    manifest = WallpaperManifest(
        date=run_date,
        generated_at=datetime.now(UTC),
        theme_family="Obsidian Terminal",
        startup_mode="Structured Start",
        wallpapers={
            "display_1": generated_wallpaper(1, "public_signal", display_1),
            "display_4": generated_wallpaper(4, "left_atmosphere", display_4),
            "display_2": generated_wallpaper(2, "center_command", display_2),
            "display_3": generated_wallpaper(3, "right_inspiration", display_3),
        },
        public_poster_path=display_1,
        public_poster_included=True,
    )
    return WallpaperManifestStore().save(manifest, output_dir / WALLPAPER_MANIFEST_NAME)


def test_doctor_reports_app_runtime_information(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(ReadinessService, "_wallpaper_api_status", lambda self: "PASS")

    lines = ReadinessService(base_path=tmp_path).doctor_lines()
    text = "\n".join(lines)

    assert "CHASEOS // DOCTOR" in text
    assert "App: ChaseOS" in text
    assert "Python:" in text
    assert "Platform:" in text
    assert "No wallpaper changes applied." in text


def test_doctor_reports_missing_comtypes_gracefully(tmp_path, monkeypatch) -> None:
    def fake_import_status(name: str) -> bool:
        return name != "comtypes"

    monkeypatch.setattr("chaseos.app.readiness.platform.system", lambda: "Windows")
    monkeypatch.setattr("chaseos.app.readiness._import_status", fake_import_status)
    monkeypatch.setattr(ReadinessService, "_wallpaper_api_status", lambda self: "FAIL missing")

    text = "\n".join(ReadinessService(base_path=tmp_path).doctor_lines())

    assert "CHASEOS // DOCTOR FAILED" in text
    assert "comtypes: FAIL" in text


def test_doctor_treats_missing_assets_as_warning_not_crash(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(ReadinessService, "_wallpaper_api_status", lambda self: "PASS")

    text = "\n".join(ReadinessService(base_path=tmp_path).doctor_lines())

    assert "Display 1 art: WARN missing" in text
    assert "Generated manifest: WARN missing" in text


def test_assets_status_reports_missing_manifest_clearly(tmp_path) -> None:
    text = "\n".join(ReadinessService(base_path=tmp_path).assets_status_lines())

    assert "No generated wallpaper manifest found." in text
    assert "/prepare wallpapers --takeaway-file <path>" in text


def test_assets_status_reports_existing_manifest_and_dimensions(tmp_path) -> None:
    write_manifest(tmp_path)

    text = "\n".join(ReadinessService(base_path=tmp_path).assets_status_lines())

    assert "Latest wallpaper manifest:" in text
    assert "Generated date: 2026-06-16" in text
    assert "Dimensions: 1920x1080" in text


def test_assets_status_warns_if_display_one_candidate_is_general_photo(tmp_path) -> None:
    public_photo = write_image(tmp_path / "photos" / "export" / "public.jpg", (1080, 1920))
    write_manifest(tmp_path, public_path=public_photo)
    service = ReadinessService(
        base_path=tmp_path,
        photo_config=PhotoSourceConfig(source_path=tmp_path / "photos" / "export"),
    )

    text = "\n".join(service.assets_status_lines())

    assert "WARN Display 1 candidate appears to come from general photos" in text


def test_prepare_wallpapers_fails_when_no_takeaway_is_provided(tmp_path) -> None:
    text = "\n".join(ReadinessService(base_path=tmp_path).prepare_wallpapers_lines(""))

    assert "CHASEOS // PREPARE WALLPAPERS FAILED" in text
    assert "Innovation takeaway is required" in text


def test_prepare_wallpapers_accepts_takeaway_text(tmp_path) -> None:
    text = "\n".join(
        ReadinessService(base_path=tmp_path).prepare_wallpapers_lines(
            '--takeaway "A useful small improvement"'
        )
    )

    assert "Wallpapers were generated only." in text


def test_prepare_wallpapers_accepts_takeaway_file(tmp_path) -> None:
    takeaway = tmp_path / "takeaway.txt"
    takeaway.write_text("A useful small improvement", encoding="utf-8")

    text = "\n".join(
        ReadinessService(base_path=tmp_path).prepare_wallpapers_lines(f"--takeaway-file {takeaway}")
    )

    assert f"Innovation takeaway source: {takeaway}" in text


def test_prepare_wallpapers_prefers_takeaway_file_when_both_are_provided(tmp_path) -> None:
    takeaway = tmp_path / "takeaway.txt"
    takeaway.write_text("File insight", encoding="utf-8")

    text = "\n".join(
        ReadinessService(base_path=tmp_path).prepare_wallpapers_lines(
            f"--takeaway-file {takeaway} --takeaway Inline insight"
        )
    )

    assert "WARN both file and text provided; using takeaway file." in text
    assert f"Innovation takeaway source: {takeaway}" in text


def test_prepare_wallpapers_writes_display_one_art_and_manifest(tmp_path) -> None:
    text = "\n".join(
        ReadinessService(base_path=tmp_path).prepare_wallpapers_lines(
            "--takeaway A useful small improvement"
        )
    )
    manifest = ReadinessService(base_path=tmp_path).planner.latest_wallpaper_manifest()

    assert "Display 1 art:" in text
    assert manifest is not None
    assert manifest.public_poster_path is not None
    assert manifest.public_poster_path.exists()
    assert manifest.wallpapers["display_4"].image_path.exists()
    assert manifest.wallpapers["display_2"].image_path.exists()
    assert manifest.wallpapers["display_3"].image_path.exists()
    assert manifest.manifest_path is not None
    assert manifest.manifest_path.exists()


def test_prepare_wallpapers_does_not_call_wallpaper_applier(tmp_path) -> None:
    sequence = StartupSequence(data_dir=tmp_path)

    response = sequence.handle_input("/prepare wallpapers --takeaway A useful small improvement")

    assert "No desktop wallpaper changes applied." in render_response_text(response)


def test_prepare_wallpapers_never_uses_lightroom_photo_for_display_one(tmp_path) -> None:
    photo_source = tmp_path / "photos" / "export"
    photo_source.mkdir(parents=True)
    write_image(photo_source / "private.jpg", (1920, 1080))
    service = ReadinessService(
        base_path=tmp_path,
        photo_config=PhotoSourceConfig(source_path=photo_source),
    )

    service.prepare_wallpapers_lines("--takeaway A useful small improvement")
    manifest = service.planner.latest_wallpaper_manifest()

    assert manifest is not None
    assert manifest.public_poster_path is not None
    assert photo_source not in manifest.public_poster_path.parents


def test_prepare_wallpapers_can_use_fallback_baseline_theme(tmp_path) -> None:
    text = "\n".join(
        ReadinessService(base_path=tmp_path).prepare_wallpapers_lines(
            "--takeaway A useful small improvement"
        )
    )

    assert "Theme source: fallback baseline theme" in text


def test_headless_command_can_run_doctor(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(ReadinessService, "_wallpaper_api_status", lambda self: "PASS")
    stdout = StringIO()

    exit_code = run_headless_cli(["--command", "/doctor"], stdout=stdout, base_path=tmp_path)

    assert exit_code == EXIT_SUCCESS
    assert "CHASEOS // DOCTOR" in stdout.getvalue()


def test_headless_command_can_run_assets_status(tmp_path) -> None:
    stdout = StringIO()

    exit_code = run_headless_cli(["--command", "/assets status"], stdout=stdout, base_path=tmp_path)

    assert exit_code == EXIT_SUCCESS
    assert "CHASEOS // ASSETS STATUS" in stdout.getvalue()


def test_headless_command_can_run_prepare_wallpapers_with_takeaway_file(tmp_path) -> None:
    takeaway = tmp_path / "takeaway.txt"
    takeaway.write_text("A useful small improvement", encoding="utf-8")
    stdout = StringIO()

    exit_code = run_headless_cli(
        ["--command", f"/prepare wallpapers --takeaway-file {takeaway}"],
        stdout=stdout,
        base_path=tmp_path,
    )

    assert exit_code == EXIT_SUCCESS
    assert "Wallpapers were generated only." in stdout.getvalue()
