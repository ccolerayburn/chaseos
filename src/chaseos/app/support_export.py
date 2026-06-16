"""Redacted support export bundle creation."""

from __future__ import annotations

import json
import os
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chaseos.storage.paths import (
    get_chaseos_data_dir,
    get_daily_session_path,
    get_daily_summary_path,
    get_exports_dir,
    get_last_apply_manifest_path,
    get_last_startup_smoke_json_path,
    get_last_wallpaper_diagnostics_path,
    get_last_wallpaper_smoke_json_path,
    get_monitor_mapping_path,
    get_previous_wallpapers_path,
)
from chaseos.wallpaper.plan import WallpaperApplyPlanner

PRIVATE_CHECK_IN_KEYS = {
    "raw_check_in",
    "check_in_text",
    "private_check_in",
    "private_checkin",
    "raw_private_check_in",
}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
PRIVATE_PHOTO_SOURCE = Path(r"C:\_Media\Photos\Lightroom\Export")


@dataclass(frozen=True)
class SupportExportResult:
    mode: str
    export_path: Path | None
    included: tuple[str, ...] = ()
    skipped: tuple[str, ...] = ()
    created: bool = False

    def lines(self) -> tuple[str, ...]:
        title = (
            "CHASEOS // SUPPORT EXPORT DRY RUN"
            if self.mode == "dry-run"
            else "CHASEOS // SUPPORT EXPORT"
        )
        lines = [title, ""]
        if self.export_path is not None:
            lines.append(f"export path: {self.export_path}")
        else:
            lines.append("export path: not created")
        lines.append("")
        lines.append("included:")
        lines.extend(f"  {item}" for item in self.included)
        if not self.included:
            lines.append("  none")
        lines.append("")
        lines.append("skipped:")
        lines.extend(f"  {item}" for item in self.skipped)
        if not self.skipped:
            lines.append("  none")
        lines.extend(("", "No wallpaper changes applied."))
        return tuple(lines)


@dataclass
class SupportExportBuilder:
    base_path: Path | str | None = None
    doctor_lines: tuple[str, ...] = ()
    version_lines: tuple[str, ...] = ()
    daily_status_lines: tuple[str, ...] = ()
    daily_summary_lines: tuple[str, ...] = ()
    extra_skips: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.base_path = Path(self.base_path) if self.base_path is not None else None
        self.app_data = get_chaseos_data_dir(self.base_path)

    def dry_run(self) -> SupportExportResult:
        bundle = self._bundle_items()
        return SupportExportResult(
            mode="dry-run",
            export_path=None,
            included=tuple(name for name, _data in bundle),
            skipped=tuple(self._skipped_items()),
            created=False,
        )

    def create_redacted(self) -> SupportExportResult:
        exports_dir = get_exports_dir(self.base_path)
        exports_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S")
        export_path = exports_dir / f"chaseos_support_{stamp}_redacted.zip"
        bundle = self._bundle_items()
        with zipfile.ZipFile(export_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for archive_name, data in bundle:
                archive.writestr(archive_name, data)
        return SupportExportResult(
            mode="redacted",
            export_path=export_path,
            included=tuple(name for name, _data in bundle),
            skipped=tuple(self._skipped_items()),
            created=True,
        )

    def _bundle_items(self) -> tuple[tuple[str, str], ...]:
        items: list[tuple[str, str]] = []
        self._add_text(items, "reports/version.txt", self.version_lines)
        self._add_text(items, "reports/doctor.txt", self.doctor_lines)
        self._add_text(items, "reports/daily_status.txt", self.daily_status_lines)
        self._add_text(items, "reports/daily_summary.txt", self.daily_summary_lines)
        self._add_json_file(
            items,
            "runtime/daily_session.json",
            get_daily_session_path(base_path=self.base_path),
        )
        self._add_text_file(
            items,
            "runtime/daily_summary.txt",
            get_daily_summary_path(base_path=self.base_path),
        )
        self._add_json_file(
            items,
            "manifests/wallpaper_manifest.json",
            self._latest_manifest_path(),
        )
        self._add_json_file(
            items,
            "manifests/public_poster_meta.json",
            self._latest_poster_meta_path(),
        )
        self._add_json_file(
            items,
            "config/monitor_mapping.json",
            get_monitor_mapping_path(self.base_path),
        )
        self._add_json_file(
            items,
            "state/last_wallpaper_diagnostics.json",
            get_last_wallpaper_diagnostics_path(self.base_path),
        )
        self._add_json_file(
            items,
            "state/last_wallpaper_smoke.json",
            get_last_wallpaper_smoke_json_path(self.base_path),
        )
        self._add_json_file(
            items,
            "state/last_startup_smoke.json",
            get_last_startup_smoke_json_path(self.base_path),
        )
        self._add_json_file(
            items,
            "state/last_apply_manifest.json",
            get_last_apply_manifest_path(self.base_path),
        )
        self._add_json_file(
            items,
            "state/previous_wallpapers.json",
            get_previous_wallpapers_path(self.base_path),
        )
        readme = Path("README.md")
        if readme.exists():
            self._add_text_file(items, "project/README.md", readme)
        return tuple(items)

    def _add_text(
        self,
        items: list[tuple[str, str]],
        archive_name: str,
        lines: tuple[str, ...],
    ) -> None:
        if lines:
            items.append((archive_name, self.redact_text("\n".join(lines) + "\n")))

    def _add_text_file(
        self,
        items: list[tuple[str, str]],
        archive_name: str,
        path: Path | None,
    ) -> None:
        if path is None or not path.exists():
            return
        if self._is_disallowed_file(path):
            return
        items.append((archive_name, self.redact_text(path.read_text(encoding="utf-8"))))

    def _add_json_file(
        self,
        items: list[tuple[str, str]],
        archive_name: str,
        path: Path | None,
    ) -> None:
        if path is None or not path.exists():
            return
        if self._is_disallowed_file(path):
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        sanitized = self.redact_json(payload)
        items.append((archive_name, json.dumps(sanitized, indent=2) + "\n"))

    def _latest_manifest_path(self) -> Path | None:
        manifest = WallpaperApplyPlanner(base_path=self.base_path).latest_wallpaper_manifest()
        return manifest.manifest_path if manifest is not None else None

    def _latest_poster_meta_path(self) -> Path | None:
        posters_dir = self.app_data / "posters"
        candidates = sorted(
            posters_dir.glob("*/public_poster_meta.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        return candidates[0] if candidates else None

    def _skipped_items(self) -> list[str]:
        skipped = [
            "generated image files (*.png, *.jpg, *.jpeg, *.webp)",
            "Lightroom/general photo files",
            "raw check-in text and full command history",
        ]
        skipped.extend(self.extra_skips)
        return skipped

    def _is_disallowed_file(self, path: Path) -> bool:
        if path.suffix.lower() in IMAGE_SUFFIXES:
            self.extra_skips.append(f"image skipped: {path.name}")
            return True
        try:
            resolved = path.resolve()
            private_source = PRIVATE_PHOTO_SOURCE.resolve()
        except OSError:
            resolved = path.absolute()
            private_source = PRIVATE_PHOTO_SOURCE.absolute()
        if private_source == resolved or private_source in resolved.parents:
            self.extra_skips.append(f"private photo source skipped: {path.name}")
            return True
        return False

    def redact_json(self, value: Any) -> Any:
        if isinstance(value, dict):
            redacted: dict[str, Any] = {}
            for key, item in value.items():
                if _is_private_key(str(key)):
                    redacted[key] = "<REDACTED>"
                else:
                    redacted[key] = self.redact_json(item)
            return redacted
        if isinstance(value, list):
            return [self.redact_json(item) for item in value]
        if isinstance(value, str):
            if self._is_external_windows_path(value):
                return "<REDACTED_EXTERNAL_PATH>"
            return self.redact_text(value)
        return value

    def redact_text(self, text: str) -> str:
        result = text
        local_app_data = os.environ.get("LOCALAPPDATA")
        user_profile = os.environ.get("USERPROFILE")
        replacements = [
            (str(PRIVATE_PHOTO_SOURCE), "<PRIVATE_PHOTO_SOURCE>"),
            (str(self.app_data), r"%LOCALAPPDATA%\ChaseOS"),
        ]
        if local_app_data:
            replacements.append((local_app_data, "%LOCALAPPDATA%"))
        if user_profile:
            replacements.append((user_profile, "%USERPROFILE%"))
        for source, replacement in replacements:
            result = result.replace(source, replacement)
        return result

    def _is_external_windows_path(self, value: str) -> bool:
        path = Path(value)
        if not path.drive:
            return False
        try:
            resolved = path.resolve()
            app_data = self.app_data.resolve()
            private_source = PRIVATE_PHOTO_SOURCE.resolve()
        except OSError:
            resolved = path.absolute()
            app_data = self.app_data.absolute()
            private_source = PRIVATE_PHOTO_SOURCE.absolute()
        if private_source == resolved or private_source in resolved.parents:
            return False
        return resolved != app_data and app_data not in resolved.parents


def _is_private_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return normalized in PRIVATE_CHECK_IN_KEYS or "raw_check_in" in normalized
