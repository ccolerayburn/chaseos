"""Thin Windows IDesktopWallpaper wrapper."""

from __future__ import annotations

import platform
from typing import Protocol


class DesktopWallpaperError(RuntimeError):
    """Raised when per-monitor wallpaper APIs are unavailable."""


class DesktopWallpaperClient(Protocol):
    def list_monitors(self) -> tuple[str, ...]:
        """Return Windows monitor IDs accepted by get/set wallpaper."""

    def get_wallpaper(self, monitor_id: str) -> str | None:
        """Return the current wallpaper path for one monitor."""

    def set_wallpaper(self, monitor_id: str, image_path: str) -> None:
        """Set one monitor wallpaper."""


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
                self._CLSID_DESKTOP_WALLPAPER
            )
        except Exception as exc:  # pragma: no cover - depends on Windows COM.
            raise DesktopWallpaperError(f"failed to initialize IDesktopWallpaper: {exc}") from exc

    def list_monitors(self) -> tuple[str, ...]:
        count = int(self._desktop_wallpaper.GetMonitorDevicePathCount())
        return tuple(
            str(self._desktop_wallpaper.GetMonitorDevicePathAt(index))
            for index in range(count)
        )

    def get_wallpaper(self, monitor_id: str) -> str | None:
        wallpaper = self._desktop_wallpaper.GetWallpaper(monitor_id)
        return str(wallpaper) if wallpaper else None

    def set_wallpaper(self, monitor_id: str, image_path: str) -> None:
        self._desktop_wallpaper.SetWallpaper(monitor_id, image_path)
