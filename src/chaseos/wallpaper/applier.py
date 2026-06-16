"""Dry-run, confirmed apply, and rollback orchestration."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from chaseos.storage.paths import get_last_apply_manifest_path
from chaseos.wallpaper.plan import WallpaperApplyPlan, WallpaperTarget
from chaseos.wallpaper.rollback import WallpaperRollbackStore
from chaseos.wallpaper.windows_desktop_wallpaper import (
    DesktopWallpaperClient,
    DesktopWallpaperError,
    WindowsDesktopWallpaper,
)


class WallpaperApplyError(RuntimeError):
    """Raised when wallpaper application or reset cannot complete."""


class WallpaperApplier:
    """Apply ChaseOS wallpaper plans with explicit confirmation only."""

    def __init__(
        self,
        client: DesktopWallpaperClient | None = None,
        base_path: Path | str | None = None,
    ) -> None:
        self.client = client
        self.base_path = Path(base_path) if base_path is not None else None
        self.rollback_store = WallpaperRollbackStore(base_path=self.base_path)

    @property
    def last_apply_manifest_path(self) -> Path:
        return get_last_apply_manifest_path(self.base_path)

    def dry_run(self, plan: WallpaperApplyPlan) -> tuple[str, ...]:
        return (
            *_plan_summary_lines(plan, title="CHASEOS // WALLPAPER APPLY DRY RUN"),
            "",
            "No changes applied.",
            "Run /apply wallpapers --confirm to apply.",
        )

    def apply_confirmed(self, plan: WallpaperApplyPlan) -> tuple[str, ...]:
        client = self._client()
        previous = {
            target.monitor_id: client.get_wallpaper(target.monitor_id)
            for target in plan.targets
        }
        self.rollback_store.save(previous)

        applied: list[WallpaperTarget] = []
        for target in plan.targets:
            client.set_wallpaper(target.monitor_id, str(target.image_path))
            applied.append(target)

        self._save_apply_manifest(plan, applied)
        return (
            "CHASEOS // WALLPAPER APPLY",
            "",
            *(
                f"{target.label}: {target.image_path}"
                for target in applied
            ),
            "",
            f"Rollback saved: {self.rollback_store.path}",
            f"Apply manifest: {self.last_apply_manifest_path}",
        )

    def reset(self) -> tuple[str, ...]:
        state = self.rollback_store.load()
        if state is None:
            raise WallpaperApplyError("no wallpaper rollback state found.")

        client = self._client()
        lines = ["CHASEOS // WALLPAPER RESET", ""]
        restored = 0
        for monitor_id, image_path in state.wallpapers.items():
            if not image_path.exists():
                lines.append(f"Skipped missing previous wallpaper for {monitor_id}: {image_path}")
                continue
            client.set_wallpaper(monitor_id, str(image_path))
            restored += 1
            lines.append(f"Restored {monitor_id}: {image_path}")
        lines.append("")
        lines.append(f"Restored wallpapers: {restored}")
        return tuple(lines)

    def _client(self) -> DesktopWallpaperClient:
        if self.client is not None:
            return self.client
        try:
            self.client = WindowsDesktopWallpaper()
        except DesktopWallpaperError as exc:
            raise WallpaperApplyError(str(exc)) from exc
        return self.client

    def _save_apply_manifest(
        self,
        plan: WallpaperApplyPlan,
        applied: list[WallpaperTarget],
    ) -> None:
        self.last_apply_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.last_apply_manifest_path.write_text(
            json.dumps(
                {
                    "applied_at": datetime.now(UTC).isoformat(),
                    "generated_date": plan.generated_date,
                    "mapping_source": plan.mapping_source,
                    "targets": [
                        {
                            **asdict(target),
                            "image_path": str(target.image_path),
                        }
                        for target in applied
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )


def _plan_summary_lines(plan: WallpaperApplyPlan, title: str) -> tuple[str, ...]:
    lines = [title, ""]
    for target in plan.targets:
        lines.extend(
            (
                target.label,
                f"  Windows monitor: {target.display_alias}",
                f"  Role: {target.role}",
                f"  Image: {target.image_path}",
                "",
            )
        )
    return tuple(lines[:-1])
