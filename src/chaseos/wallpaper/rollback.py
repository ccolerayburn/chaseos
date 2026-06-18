"""Rollback state for Windows wallpaper application."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from chaseos.storage.paths import get_previous_wallpapers_path


@dataclass(frozen=True)
class WallpaperRollbackState:
    captured_at: datetime
    wallpapers: dict[str, Path]
    position: int | None = None


class WallpaperRollbackStore:
    """Persist previous per-monitor wallpaper paths."""

    def __init__(self, base_path: Path | str | None = None) -> None:
        self.base_path = Path(base_path) if base_path is not None else None

    @property
    def path(self) -> Path:
        return get_previous_wallpapers_path(self.base_path)

    def save(
        self,
        wallpapers: dict[str, Path | str | None],
        position: int | None = None,
    ) -> WallpaperRollbackState:
        state = WallpaperRollbackState(
            captured_at=datetime.now(UTC),
            wallpapers={
                monitor_id: Path(path)
                for monitor_id, path in wallpapers.items()
                if path is not None and str(path).strip()
            },
            position=position,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {
                    "captured_at": state.captured_at.isoformat(),
                    "wallpapers": {
                        monitor_id: str(path)
                        for monitor_id, path in state.wallpapers.items()
                    },
                    "position": state.position,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return state

    def load(self) -> WallpaperRollbackState | None:
        if not self.path.exists():
            return None
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return WallpaperRollbackState(
            captured_at=datetime.fromisoformat(raw["captured_at"]),
            wallpapers={
                monitor_id: Path(path)
                for monitor_id, path in raw.get("wallpapers", {}).items()
                if str(path).strip()
            },
            position=raw.get("position"),
        )
