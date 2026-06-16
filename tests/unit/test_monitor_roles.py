import pytest

from chaseos.models.monitor import (
    DetectedMonitor,
    MonitorLayout,
    MonitorMappingConfig,
    MonitorOrientation,
    MonitorRole,
    MonitorRoleAssignment,
)
from chaseos.storage.settings_store import MonitorMappingStore
from chaseos.windows.display_detection import get_fallback_monitor_layout
from chaseos.windows.monitor_roles import (
    assign_monitor_role,
    auto_assign_known_layout,
    validate_assignments,
)


def monitor(
    stable_id: str,
    label: str | None,
    x: int,
    width: int,
    height: int,
) -> DetectedMonitor:
    return DetectedMonitor(
        stable_id=stable_id,
        display_label=label,
        x=x,
        y=0,
        width=width,
        height=height,
    )


def test_fallback_layout_contains_known_four_monitor_mapping() -> None:
    layout = get_fallback_monitor_layout()

    assert len(layout.monitors) == 4
    display_1 = next(item for item in layout.monitors if item.display_label == "display 1")
    assert display_1.width == 1080
    assert display_1.height == 1920
    assert display_1.orientation == MonitorOrientation.PORTRAIT
    for label in ("display 4", "display 2", "display 3"):
        detected = next(item for item in layout.monitors if item.display_label == label)
        assert detected.width == 1920
        assert detected.height == 1080
        assert detected.orientation == MonitorOrientation.LANDSCAPE
    assert layout.assignments[MonitorRole.PUBLIC_SIGNAL].display_label == "display 1"
    assert layout.assignments[MonitorRole.LEFT_ATMOSPHERE].display_label == "display 4"
    assert layout.assignments[MonitorRole.CENTER_COMMAND].display_label == "display 2"
    assert layout.assignments[MonitorRole.RIGHT_INSPIRATION].display_label == "display 3"


def test_manual_assignments_accept_display_and_role_aliases() -> None:
    layout = get_fallback_monitor_layout()
    layout.assignments = {}

    assign_monitor_role(layout, "display 1", "public")
    assign_monitor_role(layout, "4", "left")
    assign_monitor_role(layout, "2", "center")
    assign_monitor_role(layout, "3", "right")

    assert layout.assignments[MonitorRole.PUBLIC_SIGNAL].display_label == "display 1"
    assert layout.assignments[MonitorRole.LEFT_ATMOSPHERE].display_label == "display 4"
    assert layout.assignments[MonitorRole.CENTER_COMMAND].display_label == "display 2"
    assert layout.assignments[MonitorRole.RIGHT_INSPIRATION].display_label == "display 3"


def test_manual_assignment_invalid_role_and_display_are_friendly_errors() -> None:
    layout = get_fallback_monitor_layout()

    with pytest.raises(ValueError, match="unknown monitor role"):
        assign_monitor_role(layout, "1", "banana")
    with pytest.raises(ValueError, match="unknown display"):
        assign_monitor_role(layout, "99", "public")


def test_monitor_mapping_save_load_and_reset(tmp_path) -> None:
    layout = get_fallback_monitor_layout()
    store = MonitorMappingStore(base_path=tmp_path)

    store.save_layout(layout)
    loaded = store.load()

    assert loaded is not None
    assert loaded.assignments[MonitorRole.PUBLIC_SIGNAL].display_label == "display 1"
    assert store.exists() is True

    store.clear()

    assert store.exists() is False
    assert store.load() is None


def test_auto_assignment_uses_portrait_left_and_landscape_x_order() -> None:
    layout = MonitorLayout(
        monitors=[
            monitor("public", None, 0, 1080, 1920),
            monitor("left", None, 1080, 1920, 1080),
            monitor("center", None, 3000, 1920, 1080),
            monitor("right", None, 4920, 1920, 1080),
        ],
        detected=True,
        source="windows",
    )

    auto_assign_known_layout(layout)

    assert layout.assignments[MonitorRole.PUBLIC_SIGNAL].stable_id == "public"
    assert layout.assignments[MonitorRole.LEFT_ATMOSPHERE].stable_id == "left"
    assert layout.assignments[MonitorRole.CENTER_COMMAND].stable_id == "center"
    assert layout.assignments[MonitorRole.RIGHT_INSPIRATION].stable_id == "right"


def test_auto_assignment_prefers_windows_display_labels_when_available() -> None:
    layout = MonitorLayout(
        monitors=[
            monitor("a", "display 3", 4920, 1920, 1080),
            monitor("b", "display 1", 0, 1080, 1920),
            monitor("c", "display 2", 3000, 1920, 1080),
            monitor("d", "display 4", 1080, 1920, 1080),
        ],
        detected=True,
        source="windows",
    )

    auto_assign_known_layout(layout)

    assert layout.assignments[MonitorRole.PUBLIC_SIGNAL].stable_id == "b"
    assert layout.assignments[MonitorRole.LEFT_ATMOSPHERE].stable_id == "d"
    assert layout.assignments[MonitorRole.CENTER_COMMAND].stable_id == "c"
    assert layout.assignments[MonitorRole.RIGHT_INSPIRATION].stable_id == "a"


def test_auto_assignment_prefers_saved_stable_ids_when_still_present() -> None:
    layout = MonitorLayout(
        monitors=[
            monitor("a", "display 1", 0, 1080, 1920),
            monitor("b", "display 4", 1080, 1920, 1080),
        ],
        detected=True,
        source="windows",
    )
    saved = MonitorMappingConfig(
        assignments={
            MonitorRole.PUBLIC_SIGNAL: MonitorRoleAssignment(
                role=MonitorRole.PUBLIC_SIGNAL,
                stable_id="b",
                display_label="display 4",
            )
        }
    )

    auto_assign_known_layout(layout, saved_config=saved)

    assert layout.source == "saved"
    assert layout.assignments[MonitorRole.PUBLIC_SIGNAL].stable_id == "b"


def test_stale_saved_ids_are_warned_and_auto_assignment_continues() -> None:
    layout = MonitorLayout(
        monitors=[
            monitor("a", "display 1", 0, 1080, 1920),
            monitor("b", "display 4", 1080, 1920, 1080),
            monitor("c", "display 2", 3000, 1920, 1080),
            monitor("d", "display 3", 4920, 1920, 1080),
        ],
        detected=True,
        source="windows",
    )
    saved = MonitorMappingConfig(
        assignments={
            MonitorRole.PUBLIC_SIGNAL: MonitorRoleAssignment(
                role=MonitorRole.PUBLIC_SIGNAL,
                stable_id="missing",
                display_label="display 1",
            )
        }
    )

    auto_assign_known_layout(layout, saved_config=saved)

    assert "saved monitor mapping is stale" in " ".join(layout.warnings)
    assert layout.assignments[MonitorRole.PUBLIC_SIGNAL].stable_id == "a"
    assert validate_assignments(layout) == []
