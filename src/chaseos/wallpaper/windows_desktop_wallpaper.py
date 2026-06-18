"""Thin Windows IDesktopWallpaper wrapper."""

from __future__ import annotations

import platform
from dataclasses import dataclass
from enum import IntEnum
from typing import Protocol


class DesktopWallpaperError(RuntimeError):
    """Raised when per-monitor wallpaper APIs are unavailable."""


class DesktopWallpaperPosition(IntEnum):
    CENTER = 0
    TILE = 1
    STRETCH = 2
    FILL = 3
    FIT = 4
    SPAN = 5


@dataclass(frozen=True)
class DesktopWallpaperMonitor:
    index: int
    monitor_id: str
    wallpaper_path: str | None
    left: int | None = None
    top: int | None = None
    right: int | None = None
    bottom: int | None = None


class DesktopWallpaperClient(Protocol):
    def list_monitors(self) -> tuple[str, ...]:
        """Return Windows monitor IDs accepted by get/set wallpaper."""

    def get_wallpaper(self, monitor_id: str) -> str | None:
        """Return the current wallpaper path for one monitor."""

    def set_wallpaper(self, monitor_id: str, image_path: str) -> None:
        """Set one monitor wallpaper."""

    def get_position(self) -> int:
        """Return the global Windows desktop wallpaper position."""

    def set_position(self, position: int) -> None:
        """Set the global Windows desktop wallpaper position."""

    def describe_monitors(self) -> tuple[DesktopWallpaperMonitor, ...]:
        """Return monitor IDs with current wallpaper and bounds when available."""


class WindowsDesktopWallpaper:
    """Lazy COM wrapper around Windows IDesktopWallpaper."""

    _CLSID_DESKTOP_WALLPAPER = "{C2CF3110-460E-4fc1-B9D0-8A1C0C9CC4BD}"

    def __init__(self) -> None:
        if platform.system().lower() != "windows":
            raise DesktopWallpaperError("per-monitor wallpaper API is only available on Windows")
        try:
            import comtypes.client  # type: ignore[import-not-found]
        except ImportError as exc:
            raise DesktopWallpaperError(
                "comtypes is required for Windows per-monitor wallpaper application"
            ) from exc
        try:
            self._desktop_wallpaper = comtypes.client.CreateObject(
                self._CLSID_DESKTOP_WALLPAPER,
                interface=_desktop_wallpaper_interface(),
            )
        except Exception as exc:  # pragma: no cover - depends on Windows COM.
            raise DesktopWallpaperError(f"failed to initialize IDesktopWallpaper: {exc}") from exc

    def list_monitors(self) -> tuple[str, ...]:
        count = int(_out_value(self._desktop_wallpaper.GetMonitorDevicePathCount()))
        return tuple(
            str(_out_value(self._desktop_wallpaper.GetMonitorDevicePathAt(index)))
            for index in range(count)
        )

    def describe_monitors(self) -> tuple[DesktopWallpaperMonitor, ...]:
        monitors: list[DesktopWallpaperMonitor] = []
        for index, monitor_id in enumerate(self.list_monitors()):
            left = top = right = bottom = None
            try:
                rect = _out_value(self._desktop_wallpaper.GetMonitorRECT(monitor_id))
                left = int(rect.left)
                top = int(rect.top)
                right = int(rect.right)
                bottom = int(rect.bottom)
            except Exception:
                pass
            monitors.append(
                DesktopWallpaperMonitor(
                    index=index,
                    monitor_id=monitor_id,
                    wallpaper_path=self.get_wallpaper(monitor_id),
                    left=left,
                    top=top,
                    right=right,
                    bottom=bottom,
                )
            )
        return tuple(monitors)

    def get_wallpaper(self, monitor_id: str) -> str | None:
        wallpaper = _out_value(self._desktop_wallpaper.GetWallpaper(monitor_id))
        return str(wallpaper) if wallpaper else None

    def set_wallpaper(self, monitor_id: str, image_path: str) -> None:
        self._desktop_wallpaper.SetWallpaper(monitor_id, image_path)

    def get_position(self) -> int:
        return int(_out_value(self._desktop_wallpaper.GetPosition()))

    def set_position(self, position: int) -> None:
        self._desktop_wallpaper.SetPosition(int(position))


def _out_value(value):
    if isinstance(value, tuple) and len(value) == 1:
        return value[0]
    return value


def _desktop_wallpaper_interface():
    from ctypes import POINTER, Structure, c_int, c_uint, c_ulong, c_wchar_p

    from comtypes import COMMETHOD, GUID, HRESULT, IUnknown

    lpwstr = c_wchar_p

    class _Rect(Structure):
        _fields_ = (
            ("left", c_int),
            ("top", c_int),
            ("right", c_int),
            ("bottom", c_int),
        )

    class _IDesktopWallpaper(IUnknown):
        _case_insensitive_ = True
        _iid_ = GUID("{B92B56A9-8B55-4E14-9A89-0199BBB6F93B}")
        _methods_ = (
            COMMETHOD(
                [],
                HRESULT,
                "SetWallpaper",
                (["in"], lpwstr, "monitorID"),
                (["in"], lpwstr, "wallpaper"),
            ),
            COMMETHOD(
                [],
                HRESULT,
                "GetWallpaper",
                (["in"], lpwstr, "monitorID"),
                (["out"], POINTER(lpwstr), "wallpaper"),
            ),
            COMMETHOD(
                [],
                HRESULT,
                "GetMonitorDevicePathAt",
                (["in"], c_uint, "monitorIndex"),
                (["out"], POINTER(lpwstr), "monitorID"),
            ),
            COMMETHOD(
                [],
                HRESULT,
                "GetMonitorDevicePathCount",
                (["out"], POINTER(c_uint), "count"),
            ),
            COMMETHOD(
                [],
                HRESULT,
                "GetMonitorRECT",
                (["in"], lpwstr, "monitorID"),
                (["out"], POINTER(_Rect), "displayRect"),
            ),
            COMMETHOD([], HRESULT, "SetBackgroundColor", (["in"], c_ulong, "color")),
            COMMETHOD([], HRESULT, "GetBackgroundColor", (["out"], POINTER(c_ulong), "color")),
            COMMETHOD([], HRESULT, "SetPosition", (["in"], c_int, "position")),
            COMMETHOD([], HRESULT, "GetPosition", (["out"], POINTER(c_int), "position")),
            COMMETHOD(
                [],
                HRESULT,
                "SetSlideshow",
                (["in"], POINTER(IUnknown), "items"),
            ),
            COMMETHOD(
                [],
                HRESULT,
                "GetSlideshow",
                (["out"], POINTER(POINTER(IUnknown)), "items"),
            ),
            COMMETHOD(
                [],
                HRESULT,
                "SetSlideshowOptions",
                (["in"], c_int, "options"),
                (["in"], c_uint, "slideshowTick"),
            ),
            COMMETHOD(
                [],
                HRESULT,
                "GetSlideshowOptions",
                (["out"], POINTER(c_int), "options"),
                (["out"], POINTER(c_uint), "slideshowTick"),
            ),
            COMMETHOD(
                [],
                HRESULT,
                "AdvanceSlideshow",
                (["in"], lpwstr, "monitorID"),
                (["in"], c_int, "direction"),
            ),
            COMMETHOD([], HRESULT, "GetStatus", (["out"], POINTER(c_int), "state")),
            COMMETHOD([], HRESULT, "Enable", (["in"], c_int, "enable")),
        )

    return _IDesktopWallpaper
