"""Thin Windows IDesktopWallpaper wrapper."""

from __future__ import annotations

import platform
from dataclasses import dataclass
from typing import Protocol


class DesktopWallpaperError(RuntimeError):
    """Raised when per-monitor wallpaper APIs are unavailable."""


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

    def describe_monitors(self) -> tuple[DesktopWallpaperMonitor, ...]:
        monitors: list[DesktopWallpaperMonitor] = []
        for index, monitor_id in enumerate(self.list_monitors()):
            left = top = right = bottom = None
            try:
                rect = self._desktop_wallpaper.GetMonitorRECT(monitor_id)
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
        wallpaper = self._desktop_wallpaper.GetWallpaper(monitor_id)
        return str(wallpaper) if wallpaper else None

    def set_wallpaper(self, monitor_id: str, image_path: str) -> None:
        self._desktop_wallpaper.SetWallpaper(monitor_id, image_path)
