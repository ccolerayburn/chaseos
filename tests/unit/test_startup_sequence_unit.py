import json

import pytest
from PIL import Image

from chaseos.models.monitor import MonitorRole
from chaseos.ritual.stages import RitualStage
from chaseos.ritual.startup_sequence import StartupSequence
from chaseos.storage.daily_session_store import DailySessionStore
from chaseos.storage.paths import get_daily_session_path
from chaseos.storage.settings_store import MonitorMappingStore
from chaseos.wallpaper.applier import WallpaperApplier
from chaseos.wallpaper.photo_source import PhotoSourceConfig
from chaseos.wallpaper.windows_desktop_wallpaper import DesktopWallpaperMonitor


@pytest.fixture(autouse=True)
def use_fallback_monitor_detection(monkeypatch) -> None:
    monkeypatch.setattr("chaseos.windows.display_detection.detect_monitors", lambda: [])


def render_response_text(response) -> str:
    return "\n".join(line.render() for line in response.lines)


def advance_to_theme_approval(sequence: StartupSequence) -> None:
    sequence.handle_input("/start")
    sequence.handle_input("tired and scattered but ready to work")


def advance_to_poster_approval(sequence: StartupSequence) -> None:
    advance_to_theme_approval(sequence)
    sequence.handle_input("/approve")
    sequence.handle_input("done")
    sequence.handle_input("done")
    sequence.handle_input("we keep repeating the same troubleshooting questions")


class FakeDesktopWallpaper:
    def __init__(self) -> None:
        self.set_calls: list[tuple[str, str]] = []

    def list_monitors(self) -> tuple[str, ...]:
        return tuple(monitor.monitor_id for monitor in self.describe_monitors())

    def describe_monitors(self) -> tuple[DesktopWallpaperMonitor, ...]:
        return (
            DesktopWallpaperMonitor(0, "fallback_display_1", None, 0, 0, 1080, 1920),
            DesktopWallpaperMonitor(1, "fallback_display_4", None, 1080, 0, 3000, 1080),
            DesktopWallpaperMonitor(2, "fallback_display_2", None, 3000, 0, 4920, 1080),
            DesktopWallpaperMonitor(3, "fallback_display_3", None, 4920, 0, 6840, 1080),
        )

    def get_wallpaper(self, monitor_id: str) -> str | None:
        return None

    def set_wallpaper(self, monitor_id: str, image_path: str) -> None:
        self.set_calls.append((monitor_id, image_path))


def isolated_sequence(tmp_path) -> StartupSequence:
    fake = FakeDesktopWallpaper()
    return StartupSequence(
        data_dir=tmp_path,
        photo_config=PhotoSourceConfig(source_path=tmp_path / "missing_photos"),
        wallpaper_applier=WallpaperApplier(client=fake, base_path=tmp_path),
    )


def test_startup_sequence_starts_in_idle() -> None:
    sequence = StartupSequence()

    assert sequence.current_stage == RitualStage.IDLE
    assert sequence.is_active is False


def test_start_moves_to_check_in() -> None:
    sequence = StartupSequence()
    response = sequence.handle_input("/start")

    assert sequence.current_stage == RitualStage.CHECK_IN
    assert sequence.is_active is True
    assert "start sequence initialized." in render_response_text(response)
    assert "how are you, really?" in render_response_text(response)


def test_free_text_check_in_is_captured() -> None:
    sequence = StartupSequence()
    sequence.handle_input("/start")

    sequence.handle_input("tired and scattered but ready to work")

    assert sequence.session.raw_check_in == "tired and scattered but ready to work"


def test_daily_session_persistence_writes_practical_state_without_raw_check_in(tmp_path) -> None:
    raw_check_in = "private check in text should stay memory only"
    sequence = isolated_sequence(tmp_path)

    sequence.handle_input("/start")
    sequence.handle_input(raw_check_in)

    session_path = get_daily_session_path(base_path=tmp_path)
    payload = json.loads(session_path.read_text(encoding="utf-8"))
    assert payload["current_stage"] == "THEME_APPROVAL"
    assert payload["practical_signals"]
    assert "raw_check_in" not in payload
    assert raw_check_in not in session_path.read_text(encoding="utf-8")


def test_after_check_in_sequence_reaches_theme_approval() -> None:
    sequence = StartupSequence()

    advance_to_theme_approval(sequence)

    assert sequence.current_stage == RitualStage.THEME_APPROVAL
    assert sequence.session.startup_mode == "Structured Start"
    assert sequence.session.signals is not None
    assert sequence.session.theme_plan is not None
    assert sequence.session.current_theme_plan.startswith("THEME PLAN")


def test_approve_from_theme_approval_moves_to_mindfulness() -> None:
    sequence = StartupSequence()
    advance_to_theme_approval(sequence)

    response = sequence.handle_input("/approve")

    assert sequence.current_stage == RitualStage.MINDFULNESS
    assert sequence.session.theme_approved is True
    assert "MINDFULNESS" in render_response_text(response)


def test_change_from_theme_approval_records_request() -> None:
    sequence = StartupSequence()
    advance_to_theme_approval(sequence)
    original_plan = sequence.session.theme_plan

    response = sequence.handle_input("/change calmer")

    assert sequence.current_stage == RitualStage.THEME_APPROVAL
    assert sequence.session.theme_change_requests == ["calmer"]
    assert sequence.session.theme_plan != original_plan
    assert "theme change request recorded." in render_response_text(response)


def test_regenerate_from_theme_approval_updates_theme_plan() -> None:
    sequence = StartupSequence()
    advance_to_theme_approval(sequence)
    original_plan = sequence.session.current_theme_plan

    sequence.handle_input("/regenerate")

    assert sequence.current_stage == RitualStage.THEME_APPROVAL
    assert sequence.session.current_theme_plan != original_plan
    assert sequence.session.theme_regenerate_count == 1


def test_theme_command_prints_current_real_theme_description() -> None:
    sequence = StartupSequence()
    advance_to_theme_approval(sequence)

    response = sequence.handle_input("/theme")
    text = render_response_text(response)

    assert "THEME PLAN" in text
    assert "family .........." in text
    assert "display 1 ......." in text


def test_innovation_takeaway_is_captured() -> None:
    sequence = StartupSequence()
    advance_to_poster_approval(sequence)

    assert sequence.session.innovation_takeaway == (
        "we keep repeating the same troubleshooting questions"
    )


def test_poster_plan_does_not_include_raw_check_in() -> None:
    sequence = StartupSequence()
    advance_to_poster_approval(sequence)

    assert sequence.session.raw_check_in is not None
    assert sequence.session.raw_check_in not in sequence.session.current_poster_plan
    assert "innovation takeaway only" in sequence.session.current_poster_plan


def test_after_innovation_takeaway_reaches_poster_approval_with_real_plan() -> None:
    sequence = StartupSequence()
    advance_to_poster_approval(sequence)

    assert sequence.current_stage == RitualStage.POSTER_APPROVAL
    assert sequence.session.poster_plan is not None
    assert sequence.session.current_poster_plan.startswith("PUBLIC POSTER PLAN")
    assert "safe ............ yes" in sequence.session.current_poster_plan


def test_poster_command_prints_current_real_poster_plan() -> None:
    sequence = StartupSequence()
    advance_to_poster_approval(sequence)

    response = sequence.handle_input("/poster")
    text = render_response_text(response)

    assert "PUBLIC POSTER PLAN" in text
    assert "display ......... 1" in text


def test_change_quote_shorter_records_change_and_updates_plan() -> None:
    sequence = StartupSequence()
    advance_to_poster_approval(sequence)
    original_quote = sequence.session.public_quote

    response = sequence.handle_input("/change quote shorter")

    assert sequence.session.poster_change_requests == ["quote shorter"]
    assert sequence.session.public_quote is not None
    assert len(sequence.session.public_quote.split()) <= 5
    assert (
        sequence.session.public_quote != original_quote
        or "poster change" in render_response_text(response)
    )


def test_poster_regenerate_increments_count() -> None:
    sequence = StartupSequence()
    advance_to_poster_approval(sequence)

    sequence.handle_input("/regenerate")

    assert sequence.session.poster_regenerate_count == 1


def test_approve_from_poster_approval_renders_and_moves_to_work_ramp(tmp_path) -> None:
    sequence = isolated_sequence(tmp_path)
    advance_to_poster_approval(sequence)

    response = sequence.handle_input("/approve")

    assert sequence.current_stage == RitualStage.WORK_RAMP
    assert sequence.session.poster_approved is True
    assert sequence.session.poster_render_result is not None
    assert sequence.session.poster_render_result.image_path.exists()
    assert "WORK RAMP" in render_response_text(response)


def test_full_happy_path_reaches_complete(tmp_path) -> None:
    sequence = isolated_sequence(tmp_path)
    for user_input in (
        "/start",
        "tired and scattered but ready to work",
        "/approve",
        "done",
        "done",
        "we keep repeating the same troubleshooting questions",
        "/approve",
        "done",
    ):
        sequence.handle_input(user_input)

    assert sequence.current_stage == RitualStage.COMPLETE
    assert sequence.session.completed_at is not None
    assert sequence.timer.is_running is False
    assert sequence.session.poster_render_result is not None
    assert sequence.session.poster_render_result.image_path.exists()
    assert sequence.session.private_wallpapers_generated is True
    assert sequence.session.private_wallpaper_manifest is not None
    assert set(sequence.session.private_wallpaper_paths) == {"display_4", "display_2", "display_3"}
    assert DailySessionStore(base_path=tmp_path).load() is not None


def test_applying_stage_prints_generated_private_wallpaper_paths(tmp_path) -> None:
    sequence = isolated_sequence(tmp_path)
    for user_input in (
        "/start",
        "clear and focused",
        "/approve",
        "done",
        "done",
        "we keep repeating the same troubleshooting questions",
        "/approve",
    ):
        sequence.handle_input(user_input)

    response = sequence.handle_input("done")
    text = render_response_text(response)

    assert "GENERATING DAILY ASSETS" in text
    assert "display 4 -> left atmosphere:" in text
    assert "display 2 -> center command:" in text
    assert "display 3 -> right inspiration:" in text
    assert "CHASEOS // WALLPAPER PREFLIGHT PASSED" in text
    assert "CHASEOS // WALLPAPER APPLY DRY RUN" in text
    assert "Daily assets are ready." in text
    assert "No desktop wallpaper changes were applied." in text
    assert "Run /apply wallpapers --confirm to apply them." in text


def test_wallpapers_command_prints_paths_after_generation(tmp_path) -> None:
    sequence = isolated_sequence(tmp_path)
    for user_input in (
        "/start",
        "clear and focused",
        "/approve",
        "done",
        "done",
        "we keep repeating the same troubleshooting questions",
        "/approve",
        "done",
    ):
        sequence.handle_input(user_input)

    response = sequence.handle_input("/wallpapers")
    text = render_response_text(response)

    assert "WALLPAPER OUTPUTS" in text
    assert "display 4 -> left atmosphere:" in text


def test_daily_status_reports_no_session_clearly(tmp_path) -> None:
    response = isolated_sequence(tmp_path).handle_input("/daily status")
    text = render_response_text(response)

    assert "No daily startup session found for today." in text
    assert "Run /start to begin." in text
    assert "No wallpaper changes applied." in text


def test_daily_status_reports_existing_session_without_raw_check_in_text(tmp_path) -> None:
    raw_check_in = "raw private startup details"
    sequence = isolated_sequence(tmp_path)
    sequence.handle_input("/start")
    sequence.handle_input(raw_check_in)

    response = sequence.handle_input("/daily status")
    text = render_response_text(response)

    assert "current stage: THEME_APPROVAL" in text
    assert "theme approved: no" in text
    assert raw_check_in not in text


def test_resume_reports_no_session_clearly(tmp_path) -> None:
    response = isolated_sequence(tmp_path).handle_input("/resume")
    text = render_response_text(response)

    assert "No daily startup session found for today." in text
    assert "Run /start to begin." in text


def test_resume_loads_todays_session(tmp_path) -> None:
    sequence = isolated_sequence(tmp_path)
    sequence.handle_input("/start")
    sequence.handle_input("clear and ready")
    resumed = isolated_sequence(tmp_path)

    response = resumed.handle_input("/resume")
    text = render_response_text(response)

    assert "resumed today's daily session." in text
    assert "current stage: THEME_APPROVAL" in text
    assert resumed.current_stage == RitualStage.THEME_APPROVAL


def test_daily_status_detects_today_assets_without_session(tmp_path) -> None:
    sequence = isolated_sequence(tmp_path)
    for user_input in (
        "/start",
        "clear and focused",
        "/approve",
        "done",
        "done",
        "Clear handoffs reduce repeated work.",
        "/approve",
        "done",
    ):
        sequence.handle_input(user_input)
    get_daily_session_path(base_path=tmp_path).unlink()

    response = isolated_sequence(tmp_path).handle_input("/daily status")
    text = render_response_text(response)

    assert "No active ritual session found, but today's generated assets exist." in text
    assert "wallpaper_manifest.json" in text


def test_ritual_does_not_apply_wallpapers_automatically(tmp_path) -> None:
    fake = FakeDesktopWallpaper()
    sequence = StartupSequence(
        data_dir=tmp_path,
        photo_config=PhotoSourceConfig(source_path=tmp_path / "missing_photos"),
        wallpaper_applier=WallpaperApplier(client=fake, base_path=tmp_path),
    )
    for user_input in (
        "/start",
        "clear and focused",
        "/approve",
        "done",
        "done",
        "Clear handoffs reduce repeated work.",
        "/approve",
        "done",
    ):
        sequence.handle_input(user_input)

    assert fake.set_calls == []


def test_approve_at_work_ramp_does_not_apply_wallpapers(tmp_path) -> None:
    fake = FakeDesktopWallpaper()
    sequence = StartupSequence(
        data_dir=tmp_path,
        photo_config=PhotoSourceConfig(source_path=tmp_path / "missing_photos"),
        wallpaper_applier=WallpaperApplier(client=fake, base_path=tmp_path),
    )
    for user_input in (
        "/start",
        "clear and focused",
        "/approve",
        "done",
        "done",
        "Clear handoffs reduce repeated work.",
        "/approve",
    ):
        sequence.handle_input(user_input)

    response = sequence.handle_input("/approve")

    assert "Daily assets are ready." in render_response_text(response)
    assert fake.set_calls == []


def test_generate_wallpapers_works_when_theme_plan_exists(tmp_path) -> None:
    sequence = isolated_sequence(tmp_path)
    advance_to_theme_approval(sequence)

    response = sequence.handle_input("/generate wallpapers")

    assert sequence.session.private_wallpapers_generated is True
    assert "wallpapers generated locally." in render_response_text(response)


def test_generate_wallpapers_fails_gracefully_without_theme_plan(tmp_path) -> None:
    sequence = isolated_sequence(tmp_path)

    response = sequence.handle_input("/generate wallpapers")

    assert "no theme plan yet" in render_response_text(response)


def test_status_reports_private_wallpaper_generation_state(tmp_path) -> None:
    sequence = isolated_sequence(tmp_path)
    advance_to_theme_approval(sequence)
    sequence.handle_input("/generate wallpapers")

    response = sequence.handle_input("/status")
    text = render_response_text(response)

    assert "private wallpapers generated: yes" in text
    assert "photo index available:" in text


def test_photos_command_reports_missing_source_gracefully(tmp_path) -> None:
    sequence = StartupSequence(
        data_dir=tmp_path / "data",
        photo_config=PhotoSourceConfig(source_path=tmp_path / "missing"),
    )

    response = sequence.handle_input("/photos")
    text = render_response_text(response)

    assert "PHOTO LIBRARY" in text
    assert "source exists: no" in text
    assert "photo source not found. generated wallpapers will be used." in text
    assert "public use: disabled" in text


def test_index_photos_command_reports_missing_source_gracefully(tmp_path) -> None:
    sequence = StartupSequence(
        data_dir=tmp_path / "data",
        photo_config=PhotoSourceConfig(source_path=tmp_path / "missing"),
    )

    response = sequence.handle_input("/index photos")
    text = render_response_text(response)

    assert "photo source not found. generated wallpapers will be used." in text
    assert "public monitor photo usage remains disabled." in text


def test_photo_source_command_prints_configured_source(tmp_path) -> None:
    source = tmp_path / "photos"
    sequence = StartupSequence(
        data_dir=tmp_path / "data",
        photo_config=PhotoSourceConfig(source_path=source),
    )

    response = sequence.handle_input("/photo source")

    assert f"photo source: {source}" in render_response_text(response)


def test_index_photos_then_generate_wallpapers_uses_hybrid_for_four_and_three(
    tmp_path,
) -> None:
    source = tmp_path / "photos"
    source.mkdir()
    Image.new("RGB", (2400, 1400), (180, 120, 50)).save(source / "landscape.jpg")
    sequence = StartupSequence(
        data_dir=tmp_path / "data",
        photo_config=PhotoSourceConfig(source_path=source),
    )
    sequence.handle_input("/start")
    sequence.handle_input("clear and energized")
    sequence.handle_input("/change use more local photos")
    sequence.handle_input("/index photos")

    response = sequence.handle_input("/generate wallpapers")

    assert "wallpapers generated locally." in render_response_text(response)
    assert sequence.session.private_wallpaper_manifest is not None
    manifest = sequence.session.private_wallpaper_manifest
    assert manifest.private_selected_photos["display_4"].selected_photo_path is not None
    assert manifest.private_selected_photos["display_3"].selected_photo_path is not None
    assert manifest.private_selected_photos["display_2"].selected_photo_path is None
    assert manifest.public_monitor_uses_general_photos is False


def test_status_reports_photo_index_when_available(tmp_path) -> None:
    source = tmp_path / "photos"
    source.mkdir()
    Image.new("RGB", (1600, 900), (180, 120, 50)).save(source / "landscape.jpg")
    sequence = StartupSequence(
        data_dir=tmp_path / "data",
        photo_config=PhotoSourceConfig(source_path=source),
    )
    sequence.handle_input("/index photos")

    response = sequence.handle_input("/status")

    assert "photo index available: yes" in render_response_text(response)


def test_monitors_command_returns_fallback_layout_when_detection_fails(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("chaseos.windows.display_detection.detect_monitors", lambda: [])
    sequence = isolated_sequence(tmp_path)

    response = sequence.handle_input("/monitors")
    text = render_response_text(response)

    assert "MONITORS" in text
    assert "source .......... fallback" in text
    assert "display 1 .... 1080x1920 portrait .... public signal" in text
    assert "display 4 .... 1920x1080 landscape .... left atmosphere" in text
    assert "use /apply wallpapers --dry-run to preview wallpaper application." in text
    assert "real monitor detection unavailable" in text


def test_detect_monitors_command_is_available_without_active_ritual(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("chaseos.windows.display_detection.detect_monitors", lambda: [])
    sequence = isolated_sequence(tmp_path)

    response = sequence.handle_input("/detect monitors")

    assert "MONITORS" in render_response_text(response)
    assert sequence.current_stage == RitualStage.IDLE


def test_monitor_role_assignment_commands_save_mapping(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("chaseos.windows.display_detection.detect_monitors", lambda: [])
    sequence = isolated_sequence(tmp_path)

    sequence.handle_input("/assign display 1 public")
    sequence.handle_input("/assign 4 left")
    sequence.handle_input("/assign 2 center")
    response = sequence.handle_input("/assign 3 right")
    config = MonitorMappingStore(base_path=tmp_path).load()

    assert "assigned display 3 -> right inspiration." in render_response_text(response)
    assert config is not None
    assert config.assignments[MonitorRole.PUBLIC_SIGNAL].display_label == "display 1"
    assert config.assignments[MonitorRole.LEFT_ATMOSPHERE].display_label == "display 4"
    assert config.assignments[MonitorRole.CENTER_COMMAND].display_label == "display 2"
    assert config.assignments[MonitorRole.RIGHT_INSPIRATION].display_label == "display 3"


def test_monitor_assignment_invalid_role_and_display_return_friendly_errors(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("chaseos.windows.display_detection.detect_monitors", lambda: [])
    sequence = isolated_sequence(tmp_path)

    bad_role = sequence.handle_input("/assign 1 banana")
    bad_display = sequence.handle_input("/assign 99 public")

    assert "monitor assignment failed: unknown monitor role" in render_response_text(bad_role)
    assert "monitor assignment failed: unknown display" in render_response_text(bad_display)


def test_auto_assign_save_monitor_roles_and_reset_commands(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("chaseos.windows.display_detection.detect_monitors", lambda: [])
    sequence = isolated_sequence(tmp_path)

    auto = sequence.handle_input("/auto assign monitors")
    roles = sequence.handle_input("/monitor roles")
    save = sequence.handle_input("/save monitors")

    assert "auto-assigned monitor roles." in render_response_text(auto)
    assert "saved mapping ... yes" in render_response_text(roles)
    assert "monitor role mapping saved." in render_response_text(save)
    assert MonitorMappingStore(base_path=tmp_path).exists() is True

    reset = sequence.handle_input("/reset monitors")

    assert "saved monitor mapping cleared." in render_response_text(reset)
    assert MonitorMappingStore(base_path=tmp_path).exists() is False


def test_status_includes_monitor_mapping_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("chaseos.windows.display_detection.detect_monitors", lambda: [])
    sequence = isolated_sequence(tmp_path)
    sequence.handle_input("/auto assign monitors")

    response = sequence.handle_input("/status")
    text = render_response_text(response)

    assert "monitor mapping exists: yes" in text
    assert "monitor mapping source:" in text
    assert "public signal role assigned: yes" in text
    assert "private roles assigned: yes" in text


def test_existing_photo_command_still_works_with_monitor_phase(tmp_path) -> None:
    sequence = isolated_sequence(tmp_path)

    response = sequence.handle_input("/photos")

    assert "PHOTO LIBRARY" in render_response_text(response)


def test_public_poster_plan_and_metadata_do_not_contain_raw_check_in(tmp_path) -> None:
    raw_check_in = "slept bad and scattered but ready to work"
    sequence = isolated_sequence(tmp_path)
    sequence.handle_input("/start")
    sequence.handle_input(raw_check_in)
    sequence.handle_input("/approve")
    sequence.handle_input("done")
    sequence.handle_input("done")
    sequence.handle_input("VPN tickets keep missing hostname and username")
    sequence.handle_input("/approve")

    assert raw_check_in not in sequence.session.current_poster_plan
    assert sequence.session.poster_render_result is not None
    metadata_text = sequence.session.poster_render_result.metadata_path.read_text(encoding="utf-8")
    assert raw_check_in not in metadata_text


def test_wallpaper_manifest_does_not_contain_raw_check_in_or_innovation_takeaway(tmp_path) -> None:
    raw_check_in = "slept bad and scattered but ready to work"
    innovation_takeaway = "VPN tickets keep missing hostname and username"
    sequence = isolated_sequence(tmp_path)
    sequence.handle_input("/start")
    sequence.handle_input(raw_check_in)
    sequence.handle_input("/approve")
    sequence.handle_input("done")
    sequence.handle_input("done")
    sequence.handle_input(innovation_takeaway)
    sequence.handle_input("/approve")
    sequence.handle_input("done")

    assert sequence.session.private_wallpaper_manifest is not None
    manifest_text = sequence.session.private_wallpaper_manifest.manifest_path.read_text(
        encoding="utf-8"
    )
    assert raw_check_in not in manifest_text
    assert innovation_takeaway not in manifest_text


def test_poster_rendered_text_does_not_contain_raw_check_in(tmp_path) -> None:
    raw_check_in = "headache and private check in detail"
    sequence = isolated_sequence(tmp_path)
    sequence.handle_input("/start")
    sequence.handle_input(raw_check_in)
    sequence.handle_input("/approve")
    sequence.handle_input("done")
    sequence.handle_input("done")
    sequence.handle_input("Clear handoffs reduce repeated work.")
    sequence.handle_input("/approve")

    assert sequence.session.poster_plan is not None
    rendered_text = " ".join(
        part
        for part in (
            sequence.session.poster_plan.quote,
            sequence.session.poster_plan.subtitle or "",
            sequence.session.poster_plan.public_safe_takeaway,
        )
    )
    assert raw_check_in not in rendered_text


def test_poster_uses_display_one_and_1080x1920(tmp_path) -> None:
    sequence = isolated_sequence(tmp_path)
    advance_to_poster_approval(sequence)
    sequence.handle_input("/approve")

    assert sequence.session.poster_plan is not None
    assert sequence.session.poster_plan.display == 1
    assert sequence.session.poster_plan.width == 1080
    assert sequence.session.poster_plan.height == 1920
    assert sequence.session.poster_render_result is not None
    metadata = json.loads(
        sequence.session.poster_render_result.metadata_path.read_text(encoding="utf-8")
    )
    assert metadata["width"] == 1080
    assert metadata["height"] == 1920


def test_reset_returns_sequence_to_idle() -> None:
    sequence = StartupSequence()
    advance_to_theme_approval(sequence)

    response = sequence.handle_input("/reset")

    assert sequence.current_stage == RitualStage.IDLE
    assert sequence.is_active is False
    assert "ritual reset" in render_response_text(response)


def test_status_includes_current_stage_and_timer_information() -> None:
    sequence = StartupSequence()
    sequence.handle_input("/start")

    response = sequence.handle_input("/status")
    text = render_response_text(response)

    assert "current stage: CHECK_IN" in text
    assert "elapsed time:" in text
    assert "remaining target time:" in text
    assert "ritual active: yes" in text


def test_unknown_commands_do_not_crash() -> None:
    sequence = StartupSequence()
    sequence.handle_input("/start")

    response = sequence.handle_input("/unknown")

    assert "unknown command. type /help unless you enjoy guessing." in render_response_text(
        response
    )
