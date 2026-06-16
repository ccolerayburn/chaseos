"""Application state for the ChaseOS shell."""

from __future__ import annotations

from dataclasses import dataclass, field

from chaseos.ritual.startup_sequence import StartupSequence


@dataclass
class AppState:
    """Small mutable state container for the terminal shell."""

    status: str = "idle"
    timer_label: str = "--:--"
    sequence: StartupSequence = field(default_factory=StartupSequence)

    @property
    def header_status(self) -> str:
        return (
            f"stage: {self.sequence.current_stage.value} | "
            f"elapsed: {self.sequence.timer.elapsed_label} | "
            f"remaining: {self.sequence.timer.remaining_label}"
        )
