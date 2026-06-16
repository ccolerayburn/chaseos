from datetime import UTC, datetime, timedelta

from chaseos.ritual.timer import RITUAL_TARGET_MINUTES, RitualTimer, format_duration


def test_ritual_target_is_fifteen_minutes() -> None:
    assert RITUAL_TARGET_MINUTES == 15


def test_timer_reports_elapsed_and_remaining_time() -> None:
    timer = RitualTimer()
    timer.started_at = datetime.now(UTC) - timedelta(minutes=2, seconds=5)

    assert timer.is_running is True
    assert timer.elapsed >= timedelta(minutes=2)
    assert timer.remaining <= timedelta(minutes=13)
    assert timer.elapsed_label.startswith("02:")
    assert timer.remaining_label.startswith("12:")


def test_format_duration_uses_minutes_and_seconds() -> None:
    assert format_duration(timedelta(minutes=3, seconds=4)) == "03:04"
