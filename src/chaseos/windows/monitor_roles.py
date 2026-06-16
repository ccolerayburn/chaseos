"""ChaseOS monitor role assignment helpers."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from chaseos.models.monitor import (
    ROLE_DISPLAY_NAMES,
    ROLE_EXPECTED_ORIENTATIONS,
    DetectedMonitor,
    MonitorLayout,
    MonitorMappingConfig,
    MonitorOrientation,
    MonitorRole,
    MonitorRoleAssignment,
    resolve_monitor_role,
)

REQUIRED_PRIVATE_ROLES = (
    MonitorRole.LEFT_ATMOSPHERE,
    MonitorRole.CENTER_COMMAND,
    MonitorRole.RIGHT_INSPIRATION,
)
REQUIRED_ROLES = (MonitorRole.PUBLIC_SIGNAL, *REQUIRED_PRIVATE_ROLES)
ROLE_LABEL_ORDER = {
    "1": MonitorRole.PUBLIC_SIGNAL,
    "4": MonitorRole.LEFT_ATMOSPHERE,
    "2": MonitorRole.CENTER_COMMAND,
    "3": MonitorRole.RIGHT_INSPIRATION,
}


def assign_monitor_role(
    layout: MonitorLayout,
    display_or_stable_id: str,
    role: str | MonitorRole,
    confidence: float = 1.0,
    note: str = "manual assignment",
) -> MonitorLayout:
    """Assign one ChaseOS role to a monitor in a layout."""

    resolved_role = resolve_monitor_role(role)
    if resolved_role == MonitorRole.UNASSIGNED:
        raise ValueError("cannot assign the unassigned role")

    monitor = find_monitor(layout, display_or_stable_id)
    if monitor is None:
        raise ValueError(f"unknown display or monitor id: {display_or_stable_id}")

    assignments = {
        assignment_role: assignment
        for assignment_role, assignment in layout.assignments.items()
        if assignment.stable_id != monitor.stable_id and assignment_role != resolved_role
    }
    assignments[resolved_role] = _assignment_for_monitor(
        monitor,
        resolved_role,
        confidence=confidence,
        notes=[note],
    )
    layout.assignments = assignments
    return layout


def auto_assign_known_layout(
    layout: MonitorLayout,
    saved_config: MonitorMappingConfig | None = None,
) -> MonitorLayout:
    """Auto-assign ChaseOS roles from saved IDs, Windows labels, or geometry."""

    if saved_config is not None and _apply_saved_assignments(layout, saved_config):
        layout.source = "saved"
        return layout

    _assign_by_display_labels(layout)
    missing_roles = [role for role in REQUIRED_ROLES if role not in layout.assignments]
    if missing_roles:
        _assign_by_geometry(layout, missing_roles)

    layout.warnings.extend(validate_assignments(layout))
    return layout


def validate_assignments(layout: MonitorLayout) -> list[str]:
    """Return assignment warnings for missing, duplicate, or orientation-mismatched roles."""

    warnings: list[str] = []
    for role in REQUIRED_ROLES:
        if role not in layout.assignments:
            warnings.append(f"{ROLE_DISPLAY_NAMES[role]} role is not assigned")

    seen_stable_ids: set[str] = set()
    for role, assignment in layout.assignments.items():
        if assignment.stable_id in seen_stable_ids:
            warnings.append(f"monitor {assignment.stable_id} is assigned to multiple roles")
        seen_stable_ids.add(assignment.stable_id)

        monitor = _monitor_by_stable_id(layout, assignment.stable_id)
        expected = ROLE_EXPECTED_ORIENTATIONS.get(role)
        if monitor is not None and expected is not None and monitor.orientation != expected:
            warnings.append(
                f"{ROLE_DISPLAY_NAMES[role]} expected {expected.value}, "
                f"found {monitor.orientation.value}"
            )

    return warnings


def summarize_monitor_layout(
    layout: MonitorLayout,
    saved_mapping_exists: bool = False,
) -> tuple[str, ...]:
    """Render a concise terminal summary of detected monitors and roles."""

    lines = [
        "MONITORS",
        f"detected ........ {'yes' if layout.detected else 'no'}",
        f"source .......... {layout.source}",
        f"saved mapping ... {'yes' if saved_mapping_exists else 'no'}",
        "",
    ]
    sorted_monitors = sorted(
        layout.monitors,
        key=lambda item: (item.x, item.y, item.display_label or ""),
    )
    for monitor in sorted_monitors:
        role = _role_for_monitor(layout, monitor)
        label = monitor.display_label or monitor.stable_id
        lines.append(
            f"{label} .... {monitor.width}x{monitor.height} "
            f"{monitor.orientation.value} .... {ROLE_DISPLAY_NAMES[role]}"
        )
    lines.append("")
    lines.append("use /apply wallpapers --dry-run to preview wallpaper application.")
    return tuple(lines)


def find_monitor(layout: MonitorLayout, display_or_stable_id: str) -> DetectedMonitor | None:
    """Find a monitor by stable ID or terminal display label shorthand."""

    normalized = _normalize_display_id(display_or_stable_id)
    for monitor in layout.monitors:
        candidates = {
            monitor.stable_id.lower(),
            (monitor.device_name or "").lower(),
            (monitor.device_path or "").lower(),
            _normalize_display_id(monitor.display_label or ""),
        }
        display_number = _display_number(monitor.display_label)
        if display_number is not None:
            candidates.add(display_number)
            candidates.add(f"display {display_number}")
        if normalized in candidates:
            return monitor
    return None


def role_mapping_for_manifest(layout: MonitorLayout) -> dict[str, str]:
    """Return a compact role-to-display/stable-id map for wallpaper manifests."""

    mapping: dict[str, str] = {}
    for role, assignment in layout.assignments.items():
        mapping[role.value] = assignment.display_label or assignment.stable_id
    return mapping


def _apply_saved_assignments(layout: MonitorLayout, saved_config: MonitorMappingConfig) -> bool:
    stable_ids = {monitor.stable_id for monitor in layout.monitors}
    if not saved_config.assignments:
        return False

    stale = [
        assignment.stable_id
        for assignment in saved_config.assignments.values()
        if assignment.stable_id not in stable_ids
    ]
    if stale:
        layout.warnings.append("saved monitor mapping is stale. reassignment may be needed.")
        return False

    layout.assignments = saved_config.assignments.copy()
    return True


def _assign_by_display_labels(layout: MonitorLayout) -> None:
    for monitor in layout.monitors:
        display_number = _display_number(monitor.display_label)
        if display_number is None or display_number not in ROLE_LABEL_ORDER:
            continue
        role = ROLE_LABEL_ORDER[display_number]
        layout.assignments[role] = _assignment_for_monitor(
            monitor,
            role,
            confidence=0.98,
            notes=["assigned from Windows display label"],
        )


def _assign_by_geometry(layout: MonitorLayout, missing_roles: list[MonitorRole]) -> None:
    assigned_stable_ids = {
        assignment.stable_id for assignment in layout.assignments.values()
    }
    unassigned = [
        monitor for monitor in layout.monitors if monitor.stable_id not in assigned_stable_ids
    ]

    if MonitorRole.PUBLIC_SIGNAL in missing_roles:
        portrait = [
            monitor
            for monitor in unassigned
            if monitor.orientation == MonitorOrientation.PORTRAIT
        ]
        if portrait:
            monitor = sorted(portrait, key=lambda item: (item.x, item.y))[0]
            layout.assignments[MonitorRole.PUBLIC_SIGNAL] = _assignment_for_monitor(
                monitor,
                MonitorRole.PUBLIC_SIGNAL,
                confidence=0.82,
                notes=["left portrait monitor auto-assigned as public signal"],
            )
            unassigned = [item for item in unassigned if item.stable_id != monitor.stable_id]

    landscape = sorted(
        (
            monitor
            for monitor in unassigned
            if monitor.orientation == MonitorOrientation.LANDSCAPE
        ),
        key=lambda item: (item.x, item.y),
    )
    roles_to_assign = [role for role in REQUIRED_PRIVATE_ROLES if role not in layout.assignments]
    for role, monitor in zip(roles_to_assign, landscape, strict=False):
        layout.assignments[role] = _assignment_for_monitor(
            monitor,
            role,
            confidence=0.74,
            notes=["landscape monitor auto-assigned by x coordinate"],
        )


def _assignment_for_monitor(
    monitor: DetectedMonitor,
    role: MonitorRole,
    confidence: float,
    notes: list[str],
) -> MonitorRoleAssignment:
    return MonitorRoleAssignment(
        role=role,
        stable_id=monitor.stable_id,
        display_label=monitor.display_label,
        expected_orientation=ROLE_EXPECTED_ORIENTATIONS.get(role),
        assigned_at=datetime.now(UTC),
        confidence=confidence,
        notes=notes,
    )


def _role_for_monitor(layout: MonitorLayout, monitor: DetectedMonitor) -> MonitorRole:
    for role, assignment in layout.assignments.items():
        if assignment.stable_id == monitor.stable_id:
            return role
    return MonitorRole.UNASSIGNED


def _monitor_by_stable_id(layout: MonitorLayout, stable_id: str) -> DetectedMonitor | None:
    for monitor in layout.monitors:
        if monitor.stable_id == stable_id:
            return monitor
    return None


def _display_number(display_label: str | None) -> str | None:
    if not display_label:
        return None
    match = re.search(r"(\d+)", display_label)
    return match.group(1) if match else None


def _normalize_display_id(value: str) -> str:
    normalized = value.strip().lower().replace("_", " ")
    normalized = normalized.removeprefix("display ").strip()
    return normalized if normalized.isdigit() else value.strip().lower()
