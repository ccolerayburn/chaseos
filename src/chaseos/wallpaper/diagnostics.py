"""Wallpaper diagnostics, monitor reconciliation, and preflight validation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from chaseos.models.monitor import MonitorLayout
from chaseos.storage.paths import (
    get_last_apply_manifest_path,
    get_last_wallpaper_diagnostics_path,
)
from chaseos.wallpaper.plan import WallpaperApplyPlan, WallpaperApplyPlanner, WallpaperTarget
from chaseos.wallpaper.rollback import WallpaperRollbackStore
from chaseos.wallpaper.windows_desktop_wallpaper import (
    DesktopWallpaperClient,
    DesktopWallpaperError,
    DesktopWallpaperMonitor,
    WindowsDesktopWallpaper,
)

PASS_TITLE = "CHASEOS // WALLPAPER PREFLIGHT PASSED"
FAIL_TITLE = "CHASEOS // WALLPAPER PREFLIGHT FAILED"
STRICT_CONFIDENCES = {"exact-id", "exact-device-path", "rectangle"}


@dataclass(frozen=True)
class ReconciledWallpaperTarget:
    target: WallpaperTarget
    resolved_monitor_id: str | None
    mapping_confidence: str
    current_wallpaper_path: str | None
    image_width: int | None
    image_height: int | None
    monitor_left: int | None = None
    monitor_top: int | None = None
    monitor_right: int | None = None
    monitor_bottom: int | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class WallpaperDiagnostics:
    plan: WallpaperApplyPlan | None
    targets: tuple[ReconciledWallpaperTarget, ...]
    api_available: bool
    api_error: str | None
    warnings: tuple[str, ...]
    rollback_exists: bool
    rollback_saved_at: str | None
    rollback_entry_count: int
    rollback_missing_paths: tuple[str, ...]
    last_apply_manifest_exists: bool

    @property
    def passed(self) -> bool:
        if not self.plan or not self.api_available or self.warnings:
            return False
        monitor_ids = [target.resolved_monitor_id for target in self.targets]
        return (
            len(self.targets) == 4
            and all(monitor_ids)
            and len(set(monitor_ids)) == len(monitor_ids)
            and all(
                target.mapping_confidence in STRICT_CONFIDENCES
                and not target.warnings
                for target in self.targets
            )
        )


class WallpaperDiagnosticsService:
    """Create non-mutating wallpaper diagnostics and strict preflight results."""

    def __init__(
        self,
        planner: WallpaperApplyPlanner,
        client: DesktopWallpaperClient | None = None,
        base_path: Path | str | None = None,
    ) -> None:
        self.planner = planner
        self.client = client
        self.base_path = Path(base_path) if base_path is not None else None
        self.rollback_store = WallpaperRollbackStore(base_path=self.base_path)

    @property
    def diagnostics_path(self) -> Path:
        return get_last_wallpaper_diagnostics_path(self.base_path)

    @property
    def last_apply_manifest_path(self) -> Path:
        return get_last_apply_manifest_path(self.base_path)

    def build(self, layout: MonitorLayout) -> WallpaperDiagnostics:
        plan = None
        warnings: list[str] = []
        try:
            plan = self.planner.build_plan(layout)
        except ValueError as exc:
            warnings.append(str(exc))

        monitors, api_error = self._desktop_monitors()
        api_available = api_error is None
        targets = (
            tuple(self._reconcile_targets(plan, layout, monitors, warnings))
            if plan is not None
            else ()
        )
        rollback = self.rollback_store.load()
        rollback_missing = ()
        if rollback is not None:
            rollback_missing = tuple(
                str(path) for path in rollback.wallpapers.values() if not path.exists()
            )

        return WallpaperDiagnostics(
            plan=plan,
            targets=targets,
            api_available=api_available,
            api_error=api_error,
            warnings=tuple(warnings),
            rollback_exists=rollback is not None,
            rollback_saved_at=rollback.captured_at.isoformat() if rollback else None,
            rollback_entry_count=len(rollback.wallpapers) if rollback else 0,
            rollback_missing_paths=rollback_missing,
            last_apply_manifest_exists=self.last_apply_manifest_path.exists(),
        )

    def save(self, diagnostics: WallpaperDiagnostics) -> Path:
        self.diagnostics_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "api_available": diagnostics.api_available,
            "api_error": diagnostics.api_error,
            "warnings": list(diagnostics.warnings),
            "rollback_exists": diagnostics.rollback_exists,
            "rollback_saved_at": diagnostics.rollback_saved_at,
            "rollback_entry_count": diagnostics.rollback_entry_count,
            "rollback_missing_paths": list(diagnostics.rollback_missing_paths),
            "last_apply_manifest_exists": diagnostics.last_apply_manifest_exists,
            "targets": [
                {
                    **asdict(target),
                    "target": {
                        **asdict(target.target),
                        "image_path": str(target.target.image_path),
                    },
                }
                for target in diagnostics.targets
            ],
        }
        if diagnostics.plan is not None:
            payload["generated_date"] = diagnostics.plan.generated_date
            payload["mapping_source"] = diagnostics.plan.mapping_source
        self.diagnostics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.diagnostics_path

    def status_lines(self, layout: MonitorLayout) -> tuple[str, ...]:
        diagnostics = self.build(layout)
        manifest = self.planner.latest_wallpaper_manifest()
        poster_path = self.planner.latest_approved_public_poster()
        display_1_source = manifest.display_1_source if manifest else "unknown"
        manifest_path = manifest.manifest_path if manifest else None
        return (
            "CHASEOS // WALLPAPER STATUS",
            f"latest manifest date: {manifest.date.isoformat() if manifest else 'missing'}",
            f"latest manifest path: {manifest_path if manifest_path else 'missing'}",
            f"latest public poster: {poster_path if poster_path else 'missing'}",
            f"display 1 source: {display_1_source}",
            f"monitor mapping source: {layout.source}",
            f"rollback state exists: {'yes' if diagnostics.rollback_exists else 'no'}",
            f"rollback saved at: {diagnostics.rollback_saved_at or 'n/a'}",
            f"rollback entries: {diagnostics.rollback_entry_count}",
            f"missing rollback paths: {len(diagnostics.rollback_missing_paths)}",
            (
                "last apply manifest exists: "
                f"{'yes' if diagnostics.last_apply_manifest_exists else 'no'}"
            ),
            f"Windows per-monitor API available: {'yes' if diagnostics.api_available else 'no'}",
            *(
                (
                    "Generated wallpaper manifest missing.",
                    "Run /assets status for details.",
                )
                if manifest is None
                else ()
            ),
            "No wallpaper changes applied.",
        )

    def diagnostics_lines(self, layout: MonitorLayout) -> tuple[str, ...]:
        diagnostics = self.build(layout)
        self.save(diagnostics)
        lines = ["CHASEOS // WALLPAPER DIAGNOSTICS", ""]
        for target in diagnostics.targets:
            lines.extend(_target_lines(target))
        if self.planner.latest_approved_public_poster() is None:
            lines.append("warning: missing public poster; Display 1 may use fallback placeholder")
        if diagnostics.api_error:
            lines.append(f"warning: {diagnostics.api_error}")
        lines.extend(f"warning: {warning}" for warning in diagnostics.warnings)
        lines.extend(
            (
                f"diagnostics saved: {self.diagnostics_path}",
                "No wallpaper changes applied.",
            )
        )
        return tuple(lines)

    def verify_lines(self, layout: MonitorLayout) -> tuple[str, ...]:
        diagnostics = self.build(layout)
        issues = self.strict_issues(diagnostics)
        title = PASS_TITLE if not issues else FAIL_TITLE
        lines = [title, ""]
        for target in diagnostics.targets:
            lines.extend(_target_lines(target))
        lines.extend(f"issue: {issue}" for issue in issues)
        lines.extend(
            (
                "No changes applied.",
                (
                    "Run /apply wallpapers --confirm only if the mapping above looks correct."
                    if not issues
                    else "Fix the items above before using /apply wallpapers --confirm."
                ),
            )
        )
        return tuple(lines)

    def strict_issues(self, diagnostics: WallpaperDiagnostics) -> tuple[str, ...]:
        issues = list(diagnostics.warnings)
        if diagnostics.plan is None:
            issues.append("apply plan is unavailable")
        if not diagnostics.api_available:
            issues.append(diagnostics.api_error or "Windows per-monitor API is unavailable")
        resolved_ids = [
            target.resolved_monitor_id
            for target in diagnostics.targets
            if target.resolved_monitor_id
        ]
        if len(set(resolved_ids)) != len(resolved_ids):
            issues.append("duplicate resolved monitor IDs")
        for target in diagnostics.targets:
            issues.extend(target.warnings)
            if target.resolved_monitor_id is None:
                issues.append(f"{target.target.role} role cannot be resolved to a Windows monitor")
            if target.mapping_confidence not in STRICT_CONFIDENCES:
                issues.append(
                    f"{target.target.role} mapping confidence is {target.mapping_confidence}"
                )
        self._check_writable(self.rollback_store.path, "rollback path", issues)
        self._check_writable(self.last_apply_manifest_path, "apply manifest path", issues)
        return tuple(dict.fromkeys(issues))

    def _desktop_monitors(self) -> tuple[tuple[DesktopWallpaperMonitor, ...], str | None]:
        try:
            client = self.client or WindowsDesktopWallpaper()
            try:
                return client.describe_monitors(), None
            except Exception as exc:
                try:
                    monitors = tuple(
                        DesktopWallpaperMonitor(
                            index=index,
                            monitor_id=monitor_id,
                            wallpaper_path=client.get_wallpaper(monitor_id),
                        )
                        for index, monitor_id in enumerate(client.list_monitors())
                    )
                    return monitors, None
                except Exception:
                    return (), str(exc)
        except (DesktopWallpaperError, OSError, RuntimeError, AttributeError) as exc:
            return (), str(exc)

    def _reconcile_targets(
        self,
        plan: WallpaperApplyPlan,
        layout: MonitorLayout,
        desktop_monitors: tuple[DesktopWallpaperMonitor, ...],
        warnings: list[str],
    ) -> list[ReconciledWallpaperTarget]:
        by_id = {monitor.monitor_id: monitor for monitor in desktop_monitors}
        result = []
        for target in plan.targets:
            monitor = None
            confidence = "unresolved"
            layout_monitor = _layout_monitor(layout, target.monitor_id)
            if target.monitor_id in by_id:
                monitor = by_id[target.monitor_id]
                confidence = "exact-id"
            elif layout_monitor and layout_monitor.device_path in by_id:
                monitor = by_id[str(layout_monitor.device_path)]
                confidence = "exact-device-path"
            elif layout_monitor:
                monitor = _match_rectangle(layout_monitor, desktop_monitors)
                if monitor is not None:
                    confidence = "rectangle"

            target_warnings = list(_image_warnings(target, self.planner))
            if monitor is None:
                target_warnings.append("role cannot be resolved to a Windows monitor")
            width, height = _image_dimensions(target.image_path)
            if width is None or height is None:
                target_warnings.append(f"image is not a readable image file: {target.image_path}")
            if (
                target.role == "public"
                and target.source == "approved_public_poster"
                and (width, height) != (1080, 1920)
            ):
                target_warnings.append("approved public poster is not 1080x1920")
            result.append(
                ReconciledWallpaperTarget(
                    target=target,
                    resolved_monitor_id=monitor.monitor_id if monitor else None,
                    mapping_confidence=confidence,
                    current_wallpaper_path=monitor.wallpaper_path if monitor else None,
                    image_width=width,
                    image_height=height,
                    monitor_left=monitor.left if monitor else None,
                    monitor_top=monitor.top if monitor else None,
                    monitor_right=monitor.right if monitor else None,
                    monitor_bottom=monitor.bottom if monitor else None,
                    warnings=tuple(target_warnings),
                )
            )
        return result

    def _check_writable(self, path: Path, label: str, issues: list[str]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            probe = path.parent / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        except OSError as exc:
            issues.append(f"{label} is not writable: {exc}")


def _target_lines(target: ReconciledWallpaperTarget) -> list[str]:
    bounds = (
        f"{target.monitor_left},{target.monitor_top},"
        f"{target.monitor_right},{target.monitor_bottom}"
        if target.monitor_left is not None
        else "unavailable"
    )
    dimensions = (
        f"{target.image_width}x{target.image_height}"
        if target.image_width and target.image_height
        else "unreadable"
    )
    lines = [
        target.target.label,
        f"  Role: {target.target.role}",
        f"  Display alias: {target.target.display_alias}",
        f"  Image: {target.target.image_path}",
        f"  Image source: {_source_label(target.target)}",
        f"  Image dimensions: {dimensions}",
        f"  Resolved monitor ID: {target.resolved_monitor_id or 'unresolved'}",
        f"  Mapping confidence: {target.mapping_confidence}",
        f"  Current wallpaper: {target.current_wallpaper_path or 'unavailable'}",
        f"  Monitor bounds: {bounds}",
    ]
    lines.extend(f"  Warning: {warning}" for warning in target.warnings)
    lines.append("")
    return lines


def _source_label(target: WallpaperTarget) -> str:
    if target.source == "approved_public_poster":
        return "public_poster"
    if target.source == "placeholder_public_signal":
        return "display_1_placeholder"
    return "generated_manifest"


def _layout_monitor(layout: MonitorLayout, stable_id: str):
    for monitor in layout.monitors:
        if monitor.stable_id == stable_id:
            return monitor
    return None


def _match_rectangle(layout_monitor, desktop_monitors):
    right = layout_monitor.x + layout_monitor.width
    bottom = layout_monitor.y + layout_monitor.height
    for monitor in desktop_monitors:
        if (
            monitor.left == layout_monitor.x
            and monitor.top == layout_monitor.y
            and monitor.right == right
            and monitor.bottom == bottom
        ):
            return monitor
    return None


def _image_dimensions(path: Path) -> tuple[int | None, int | None]:
    try:
        with Image.open(path) as image:
            image.verify()
            return image.size
    except (OSError, UnidentifiedImageError):
        return None, None


def _image_warnings(target: WallpaperTarget, planner: WallpaperApplyPlanner) -> tuple[str, ...]:
    warnings = []
    if not target.image_path.exists():
        warnings.append(f"missing generated wallpaper: {target.image_path}")
    if target.role == "public" and planner._is_general_photo_path(target.image_path):
        warnings.append("public image path appears to come from Lightroom/general photos")
    return tuple(warnings)
