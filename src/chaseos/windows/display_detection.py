"""Windows display detection with a ChaseOS fallback layout."""

from __future__ import annotations

import ctypes
import platform
import re
from ctypes import POINTER, Structure, byref, c_int, c_long, c_ulong, c_void_p
from datetime import UTC, datetime

from chaseos.models.monitor import (
    DetectedMonitor,
    MonitorLayout,
    MonitorRole,
    MonitorRoleAssignment,
)

KNOWN_DISPLAY_ROLES = {
    1: "public_signal",
    4: "left_atmosphere",
    2: "center_command",
    3: "right_inspiration",
}

_FALLBACK_MONITORS = (
    (1, "fallback_display_1", "display 1", 0, 0, 1080, 1920, "public_signal"),
    (4, "fallback_display_4", "display 4", 1080, 0, 1920, 1080, "left_atmosphere"),
    (2, "fallback_display_2", "display 2", 3000, 0, 1920, 1080, "center_command"),
    (3, "fallback_display_3", "display 3", 4920, 0, 1920, 1080, "right_inspiration"),
)


class _Rect(Structure):
    _fields_ = (
        ("left", c_long),
        ("top", c_long),
        ("right", c_long),
        ("bottom", c_long),
    )


class _MonitorInfoEx(Structure):
    _fields_ = (
        ("cbSize", c_ulong),
        ("rcMonitor", _Rect),
        ("rcWork", _Rect),
        ("dwFlags", c_ulong),
        ("szDevice", ctypes.c_wchar * 32),
    )


def detect_monitors() -> list[DetectedMonitor]:
    """Detect connected monitors on Windows, returning an empty list on failure."""

    if platform.system().lower() != "windows":
        return []

    try:
        return _detect_windows_monitors()
    except (AttributeError, OSError, ValueError):
        return []


def detect_monitor_layout(use_fallback: bool = True) -> MonitorLayout:
    """Return a detected monitor layout or the known ChaseOS fallback."""

    monitors = detect_monitors()
    if monitors:
        return MonitorLayout(
            detected_at=datetime.now(UTC),
            monitors=monitors,
            detected=True,
            source="windows",
        )
    if use_fallback:
        return get_fallback_monitor_layout()
    return MonitorLayout(
        detected_at=datetime.now(UTC),
        monitors=[],
        detected=False,
        source="unavailable",
        warnings=["real monitor detection unavailable"],
    )


def get_fallback_monitor_layout() -> MonitorLayout:
    """Return the known four-display ChaseOS layout."""

    monitors = [
        DetectedMonitor(
            stable_id=stable_id,
            display_label=display_label,
            device_name=None,
            device_path=None,
            x=x,
            y=y,
            width=width,
            height=height,
            is_primary=display_id == 2,
            raw={"fallback": True, "display_id": display_id},
        )
        for display_id, stable_id, display_label, x, y, width, height, _role in _FALLBACK_MONITORS
    ]
    assignments = {
        MonitorRole(role): MonitorRoleAssignment(
            role=MonitorRole(role),
            stable_id=stable_id,
            display_label=display_label,
            confidence=1.0,
            notes=["known ChaseOS fallback layout"],
        )
        for (
            _display_id,
            stable_id,
            display_label,
            _x,
            _y,
            _width,
            _height,
            role,
        ) in _FALLBACK_MONITORS
    }
    return MonitorLayout(
        detected_at=datetime.now(UTC),
        monitors=monitors,
        assignments=assignments,
        detected=False,
        source="fallback",
        warnings=["real monitor detection unavailable. using known ChaseOS fallback layout."],
    )


def _detect_windows_monitors() -> list[DetectedMonitor]:
    user32 = ctypes.windll.user32
    monitors: list[DetectedMonitor] = []

    monitor_enum_proc = ctypes.WINFUNCTYPE(
        c_int,
        c_void_p,
        c_void_p,
        POINTER(_Rect),
        c_void_p,
    )

    def callback(
        monitor_handle: c_void_p,
        _device_context: c_void_p,
        _rect_pointer: POINTER(_Rect),
        _data: c_void_p,
    ) -> int:
        info = _MonitorInfoEx()
        info.cbSize = c_ulong(sizeof_monitor_info_ex())
        if not user32.GetMonitorInfoW(monitor_handle, byref(info)):
            return 1

        left = int(info.rcMonitor.left)
        top = int(info.rcMonitor.top)
        right = int(info.rcMonitor.right)
        bottom = int(info.rcMonitor.bottom)
        width = right - left
        height = bottom - top
        device_name = str(info.szDevice).rstrip("\x00") or None
        display_label = _display_label_from_device_name(device_name)
        stable_id = device_name or f"monitor:{left},{top},{width}x{height}"
        monitors.append(
            DetectedMonitor(
                stable_id=stable_id,
                display_label=display_label,
                device_name=device_name,
                device_path=device_name,
                x=left,
                y=top,
                width=width,
                height=height,
                is_primary=bool(info.dwFlags & 1),
                raw={
                    "source": "EnumDisplayMonitors",
                    "monitor_rect": [left, top, right, bottom],
                },
            )
        )
        return 1

    user32.EnumDisplayMonitors(0, 0, monitor_enum_proc(callback), 0)
    return sorted(monitors, key=lambda monitor: (monitor.x, monitor.y, monitor.stable_id))


def _display_label_from_device_name(device_name: str | None) -> str | None:
    if not device_name:
        return None
    match = re.search(r"DISPLAY(\d+)", device_name, re.IGNORECASE)
    if not match:
        return None
    return f"display {match.group(1)}"


def sizeof_monitor_info_ex() -> int:
    return 40 + (32 * 2)
