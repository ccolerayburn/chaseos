from chaseos.ritual.stages import RitualStage
from chaseos.ritual.startup_sequence import STARTUP_SEQUENCE_STAGES, StartupSequence
from chaseos.wallpaper.photo_source import PhotoSourceConfig


def test_startup_sequence_has_phase_three_stages() -> None:
    assert STARTUP_SEQUENCE_STAGES[0] == "IDLE"
    assert "THEME_APPROVAL" in STARTUP_SEQUENCE_STAGES
    assert "POSTER_APPROVAL" in STARTUP_SEQUENCE_STAGES
    assert "COMPLETE" in STARTUP_SEQUENCE_STAGES


def test_full_text_only_ritual_flow_without_gui(tmp_path) -> None:
    sequence = StartupSequence(
        data_dir=tmp_path,
        photo_config=PhotoSourceConfig(source_path=tmp_path / "missing_photos"),
    )
    inputs = (
        "/start",
        "tired and scattered but ready to work",
        "/approve",
        "done",
        "done",
        "we keep repeating the same troubleshooting questions",
        "/approve",
        "done",
    )

    for user_input in inputs:
        sequence.handle_input(user_input)

    assert sequence.current_stage == RitualStage.COMPLETE
    assert sequence.session.raw_check_in == "tired and scattered but ready to work"
    assert sequence.session.innovation_takeaway == (
        "we keep repeating the same troubleshooting questions"
    )
    assert sequence.session.raw_check_in not in sequence.session.current_poster_plan
    assert sequence.session.current_poster_plan.startswith("PUBLIC POSTER PLAN")
    assert sequence.session.poster_render_result is not None
    assert sequence.session.poster_render_result.image_path.exists()
    assert sequence.session.private_wallpapers_generated is True
    assert sequence.session.private_wallpaper_manifest is not None
