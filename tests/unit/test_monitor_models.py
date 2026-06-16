from datetime import UTC, datetime

from chaseos.models.monitor import (
    ROLE_ALIASES,
    DetectedMonitor,
    MonitorLayout,
    MonitorOrientation,
    MonitorRole,
    MonitorRoleAssignment,
    resolve_monitor_role,
)


def test_detected_monitor_orientation_is_calculated() -> None:
    portrait = DetectedMonitor(stable_id="p", x=0, y=0, width=1080, height=1920)
    landscape = DetectedMonitor(stable_id="l", x=0, y=0, width=1920, height=1080)
    square = DetectedMonitor(stable_id="s", x=0, y=0, width=1000, height=1000)

    assert portrait.orientation == MonitorOrientation.PORTRAIT
    assert landscape.orientation == MonitorOrientation.LANDSCAPE
    assert square.orientation == MonitorOrientation.SQUARE


def test_monitor_role_aliases_resolve() -> None:
    assert resolve_monitor_role("public") == MonitorRole.PUBLIC_SIGNAL
    assert resolve_monitor_role("poster") == MonitorRole.PUBLIC_SIGNAL
    assert resolve_monitor_role("left") == MonitorRole.LEFT_ATMOSPHERE
    assert resolve_monitor_role("main") == MonitorRole.CENTER_COMMAND
    assert resolve_monitor_role("inspiration") == MonitorRole.RIGHT_INSPIRATION
    assert ROLE_ALIASES["display4"] == MonitorRole.LEFT_ATMOSPHERE


def test_monitor_role_assignment_serializes_and_deserializes() -> None:
    assignment = MonitorRoleAssignment(
        role=MonitorRole.PUBLIC_SIGNAL,
        stable_id="display-1",
        display_label="display 1",
        assigned_at=datetime.now(UTC),
        confidence=0.9,
    )

    loaded = MonitorRoleAssignment.model_validate_json(assignment.model_dump_json())

    assert loaded.role == MonitorRole.PUBLIC_SIGNAL
    assert loaded.expected_orientation == MonitorOrientation.PORTRAIT
    assert loaded.display_label == "display 1"


def test_monitor_layout_serializes_and_deserializes() -> None:
    layout = MonitorLayout(
        monitors=[DetectedMonitor(stable_id="display-1", x=0, y=0, width=1080, height=1920)],
        assignments={
            MonitorRole.PUBLIC_SIGNAL: MonitorRoleAssignment(
                role=MonitorRole.PUBLIC_SIGNAL,
                stable_id="display-1",
                display_label="display 1",
            )
        },
        detected=True,
        source="windows",
    )

    loaded = MonitorLayout.model_validate_json(layout.model_dump_json())

    assert loaded.monitors[0].orientation == MonitorOrientation.PORTRAIT
    assert loaded.assignments[MonitorRole.PUBLIC_SIGNAL].stable_id == "display-1"
    assert loaded.source == "windows"
