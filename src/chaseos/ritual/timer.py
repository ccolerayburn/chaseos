"""Timer helpers for the ChaseOS startup ritual."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

RITUAL_TARGET_MINUTES = 15


def format_duration(duration: timedelta) -> str:
    """Format a duration as MM:SS for the terminal header."""

    total_seconds = max(0, int(duration.total_seconds()))
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


@dataclass
class RitualTimer:
    """Non-blocking ritual timer state."""

    target_minutes: int = RITUAL_TARGET_MINUTES
    started_at: datetime | None = None
    stopped_at: datetime | None = None

    @property
    def target_duration(self) -> timedelta:
        return timedelta(minutes=self.target_minutes)

    @property
    def is_running(self) -> bool:
        return self.started_at is not None and self.stopped_at is None

    def start(self) -> None:
        self.started_at = datetime.now(UTC)
        self.stopped_at = None

    def stop(self) -> None:
        if self.started_at is not None and self.stopped_at is None:
            self.stopped_at = datetime.now(UTC)

    def reset(self) -> None:
        self.started_at = None
        self.stopped_at = None

    @property
    def elapsed(self) -> timedelta:
        if self.started_at is None:
            return timedelta()
        end = self.stopped_at or datetime.now(UTC)
        return max(timedelta(), end - self.started_at)

    @property
    def remaining(self) -> timedelta:
        return max(timedelta(), self.target_duration - self.elapsed)

    @property
    def elapsed_label(self) -> str:
        return format_duration(self.elapsed)

    @property
    def remaining_label(self) -> str:
        return format_duration(self.remaining)
