"""Dry-run, confirmed apply, and rollback orchestration."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from chaseos.storage.paths import get_last_apply_manifest_path
from chaseos.wallpaper.plan import WallpaperApplyPlan, WallpaperTarget
from chaseos.wallpaper.rollback import WallpaperRollbackStore
from chaseos.wallpaper.windows_desktop_wallpaper import (
    DesktopWallpaperClient,
    DesktopWallpaperError,
    DesktopWallpaperPosition,
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

    def dry_run(self, plan: WallpaperApplyPlan, diagnostics=None) -> tuple[str, ...]:
        if diagnostics is not None and diagnostics.targets:
            return (
                "CHASEOS // WALLPAPER APPLY DRY RUN",
                "",
                *_diagnostic_target_lines(diagnostics.targets),
                "No changes applied.",
                "Run /apply wallpapers --confirm to apply.",
            )
        return (
            *_plan_summary_lines(plan, title="CHASEOS // WALLPAPER APPLY DRY RUN"),
            "",
            "No changes applied.",
            "Run /apply wallpapers --confirm to apply.",
        )

    def apply_confirmed(
        self,
        plan: WallpaperApplyPlan,
        resolved_monitor_ids: dict[str, str] | None = None,
    ) -> tuple[str, ...]:
        client = self._client()
        resolved_monitor_ids = resolved_monitor_ids or {
            target.monitor_id: target.monitor_id for target in plan.targets
        }
        previous = {
            resolved_monitor_ids[target.monitor_id]: client.get_wallpaper(
                resolved_monitor_ids[target.monitor_id]
            )
            for target in plan.targets
        }
        previous_position = client.get_position()
        if previous_position == DesktopWallpaperPosition.SPAN:
            client.set_position(DesktopWallpaperPosition.FILL)
        self.rollback_store.save(previous, position=int(previous_position))

        verified: list[tuple[WallpaperTarget, str]] = []
        failed: list[tuple[WallpaperTarget, str, str | None]] = []
        for target in plan.targets:
            monitor_id = resolved_monitor_ids[target.monitor_id]
            try:
                client.set_wallpaper(monitor_id, str(target.image_path))
            except Exception as exc:
                failed.append((target, monitor_id, f"set failed: {exc}"))
                continue
            actual = client.get_wallpaper(monitor_id)
            if _same_wallpaper_path(actual, target.image_path):
                verified.append((target, monitor_id))
            else:
                failed.append((target, monitor_id, actual))

        self._save_apply_manifest(plan, verified, failed)
        position_line = (
            "Wallpaper position: Span detected; changed to Fill for per-monitor apply."
            if previous_position == DesktopWallpaperPosition.SPAN
            else f"Wallpaper position: {_wallpaper_position_name(previous_position)}."
        )
        warning_lines = tuple(
            (
                "WARNING: "
                f"{target.label} did not change "
                f"(monitor: {monitor_id}; "
                f"expected: {target.image_path}; current: {actual or 'n/a'})"
            )
            for target, monitor_id, actual in failed
        )
        return (
            "CHASEOS // WALLPAPER APPLY",
            "",
            position_line,
            "",
            "Verified monitors:",
            *(f"{target.label}: {target.image_path}" for target, _monitor_id in verified),
            *(("none",) if not verified else ()),
            "",
            "Unverified or failed monitors:",
            *warning_lines,
            *(("none",) if not failed else ()),
            "",
            f"Verified: {len(verified)}",
            f"Unverified or failed: {len(failed)}",
            f"Rollback saved: {self.rollback_store.path}",
            f"Apply manifest: {self.last_apply_manifest_path}",
        )

    def reset(self) -> tuple[str, ...]:
        state = self.rollback_store.load()
        if state is None:
            raise WallpaperApplyError("no wallpaper rollback state found.")

        client = self._client()
        lines = ["CHASEOS // WALLPAPER RESET", ""]
        if state.position is not None:
            client.set_position(state.position)
            position_name = _wallpaper_position_name(state.position)
            lines.append(f"Restored wallpaper position: {position_name}")
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
        verified: list[tuple[WallpaperTarget, str]],
        failed: list[tuple[WallpaperTarget, str, str | None]],
    ) -> None:
        self.last_apply_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.last_apply_manifest_path.write_text(
            json.dumps(
                {
                    "applied_at": datetime.now(UTC).isoformat(),
                    "generated_date": plan.generated_date,
                    "mapping_source": plan.mapping_source,
                    "verified_count": len(verified),
                    "failed_count": len(failed),
                    "verified_targets": [
                        {
                            **asdict(target),
                            "monitor_id": monitor_id,
                            "image_path": str(target.image_path),
                            "verified": True,
                        }
                        for target, monitor_id in verified
                    ],
                    "failed_targets": [
                        {
                            **asdict(target),
                            "monitor_id": monitor_id,
                            "image_path": str(target.image_path),
                            "verified": False,
                            "actual_path": actual,
                        }
                        for target, monitor_id, actual in failed
                    ],
                    "targets": [
                        {
                            **asdict(target),
                            "monitor_id": monitor_id,
                            "image_path": str(target.image_path),
                            "verified": True,
                        }
                        for target, monitor_id in verified
                    ]
                    + [
                        {
                            **asdict(target),
                            "monitor_id": monitor_id,
                            "image_path": str(target.image_path),
                            "verified": False,
                            "actual_path": actual,
                        }
                        for target, monitor_id, actual in failed
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )


def _same_wallpaper_path(actual: str | None, expected: Path) -> bool:
    if actual is None:
        return False
    actual_path = os.path.normcase(os.path.normpath(actual))
    expected_path = os.path.normcase(os.path.normpath(str(expected)))
    return actual_path == expected_path


def _wallpaper_position_name(position: int) -> str:
    try:
        return DesktopWallpaperPosition(position).name.lower()
    except ValueError:
        return f"unknown:{position}"


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


def _diagnostic_target_lines(targets) -> tuple[str, ...]:
    lines: list[str] = []
    for reconciled in targets:
        target = reconciled.target
        dimensions = (
            f"{reconciled.image_width}x{reconciled.image_height}"
            if reconciled.image_width and reconciled.image_height
            else "unreadable"
        )
        lines.extend(
            (
                target.label,
                f"  Role: {target.role}",
                f"  Display alias: {target.display_alias}",
                f"  Image: {target.image_path}",
                f"  Image source: {_source_label(target)}",
                f"  Image dimensions: {dimensions}",
                (
                    "  Resolved IDesktopWallpaper monitor ID: "
                    f"{reconciled.resolved_monitor_id or 'unresolved'}"
                ),
                f"  Mapping confidence: {reconciled.mapping_confidence}",
            )
        )
        lines.extend(f"  Warning: {warning}" for warning in reconciled.warnings)
        lines.append("")
    return tuple(lines)


def _source_label(target: WallpaperTarget) -> str:
    if target.source == "approved_public_poster":
        return "public_poster"
    if target.source == "placeholder_public_signal":
        return "display_1_placeholder"
    return "generated_manifest"
