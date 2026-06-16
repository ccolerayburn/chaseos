"""Monitor detection and ChaseOS role mapping models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class MonitorOrientation(StrEnum):
    """Physical monitor orientation derived from geometry."""

    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    SQUARE = "square"


class MonitorRole(StrEnum):
    """ChaseOS monitor roles."""

    PUBLIC_SIGNAL = "public_signal"
    LEFT_ATMOSPHERE = "left_atmosphere"
    CENTER_COMMAND = "center_command"
    RIGHT_INSPIRATION = "right_inspiration"
    UNASSIGNED = "unassigned"


ROLE_DISPLAY_NAMES = {
    MonitorRole.PUBLIC_SIGNAL: "public signal",
    MonitorRole.LEFT_ATMOSPHERE: "left atmosphere",
    MonitorRole.CENTER_COMMAND: "center command",
    MonitorRole.RIGHT_INSPIRATION: "right inspiration",
    MonitorRole.UNASSIGNED: "unassigned",
}

ROLE_EXPECTED_ORIENTATIONS = {
    MonitorRole.PUBLIC_SIGNAL: MonitorOrientation.PORTRAIT,
    MonitorRole.LEFT_ATMOSPHERE: MonitorOrientation.LANDSCAPE,
    MonitorRole.CENTER_COMMAND: MonitorOrientation.LANDSCAPE,
    MonitorRole.RIGHT_INSPIRATION: MonitorOrientation.LANDSCAPE,
}

ROLE_ALIASES = {
    "public": MonitorRole.PUBLIC_SIGNAL,
    "public_signal": MonitorRole.PUBLIC_SIGNAL,
    "signal": MonitorRole.PUBLIC_SIGNAL,
    "poster": MonitorRole.PUBLIC_SIGNAL,
    "display1": MonitorRole.PUBLIC_SIGNAL,
    "display_1": MonitorRole.PUBLIC_SIGNAL,
    "left": MonitorRole.LEFT_ATMOSPHERE,
    "left_atmosphere": MonitorRole.LEFT_ATMOSPHERE,
    "atmosphere": MonitorRole.LEFT_ATMOSPHERE,
    "display4": MonitorRole.LEFT_ATMOSPHERE,
    "display_4": MonitorRole.LEFT_ATMOSPHERE,
    "center": MonitorRole.CENTER_COMMAND,
    "center_command": MonitorRole.CENTER_COMMAND,
    "command": MonitorRole.CENTER_COMMAND,
    "main": MonitorRole.CENTER_COMMAND,
    "display2": MonitorRole.CENTER_COMMAND,
    "display_2": MonitorRole.CENTER_COMMAND,
    "right": MonitorRole.RIGHT_INSPIRATION,
    "right_inspiration": MonitorRole.RIGHT_INSPIRATION,
    "inspiration": MonitorRole.RIGHT_INSPIRATION,
    "display3": MonitorRole.RIGHT_INSPIRATION,
    "display_3": MonitorRole.RIGHT_INSPIRATION,
    "unassigned": MonitorRole.UNASSIGNED,
}


def calculate_orientation(width: int, height: int) -> MonitorOrientation:
    """Return a simple orientation label for a monitor rectangle."""

    if height > width:
        return MonitorOrientation.PORTRAIT
    if width > height:
        return MonitorOrientation.LANDSCAPE
    return MonitorOrientation.SQUARE


def resolve_monitor_role(value: str | MonitorRole) -> MonitorRole:
    """Resolve terminal role aliases into a ChaseOS role."""

    if isinstance(value, MonitorRole):
        return value
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    normalized = normalized.removeprefix("/")
    if normalized in ROLE_ALIASES:
        return ROLE_ALIASES[normalized]
    try:
        return MonitorRole(normalized)
    except ValueError as exc:
        raise ValueError(f"unknown monitor role: {value}") from exc


class DetectedMonitor(BaseModel):
    """One detected Windows monitor rectangle."""

    stable_id: str
    display_label: str | None = None
    device_name: str | None = None
    device_path: str | None = None
    x: int
    y: int
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    orientation: MonitorOrientation | None = None
    is_primary: bool | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def set_orientation(self) -> DetectedMonitor:
        if self.orientation is None:
            self.orientation = calculate_orientation(self.width, self.height)
        return self


class MonitorRoleAssignment(BaseModel):
    """Assignment of a ChaseOS role to a detected monitor."""

    role: MonitorRole
    stable_id: str
    display_label: str | None = None
    expected_orientation: MonitorOrientation | None = None
    assigned_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def set_expected_orientation(self) -> MonitorRoleAssignment:
        if self.expected_orientation is None:
            self.expected_orientation = ROLE_EXPECTED_ORIENTATIONS.get(self.role)
        return self


class MonitorLayout(BaseModel):
    """Detected monitor layout plus ChaseOS role assignments."""

    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    monitors: list[DetectedMonitor] = Field(default_factory=list)
    assignments: dict[MonitorRole, MonitorRoleAssignment] = Field(default_factory=dict)
    detected: bool = False
    source: str = "unknown"
    warnings: list[str] = Field(default_factory=list)


class MonitorMappingConfig(BaseModel):
    """Persisted monitor role mapping."""

    saved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    assignments: dict[MonitorRole, MonitorRoleAssignment] = Field(default_factory=dict)
    source: str = "saved"
    notes: list[str] = Field(default_factory=list)
