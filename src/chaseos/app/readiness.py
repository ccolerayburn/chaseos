"""First-run readiness, asset status, and safe asset preparation."""

from __future__ import annotations

import importlib.util
import platform
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from chaseos import __version__
from chaseos.models.assets import WallpaperManifest
from chaseos.models.signals import PracticalSignals, StartupMode
from chaseos.models.theme import ThemePlan
from chaseos.poster.art_engine import Display1ArtEngine
from chaseos.storage.paths import (
    get_chaseos_data_dir,
    get_config_dir,
    get_last_wallpaper_diagnostics_path,
    get_last_wallpaper_smoke_json_path,
    get_monitor_mapping_path,
    get_previous_wallpapers_path,
    get_wallpaper_state_dir,
)
from chaseos.theming.theme_generator import ThemeGenerator
from chaseos.wallpaper.photo_source import PhotoSourceConfig
from chaseos.wallpaper.plan import WallpaperApplyPlanner
from chaseos.wallpaper.wallpaper_composer import WallpaperComposer
from chaseos.wallpaper.windows_desktop_wallpaper import (
    DesktopWallpaperError,
    WindowsDesktopWallpaper,
)


@dataclass(frozen=True)
class PreparedAssets:
    poster_path: Path
    poster_metadata_path: Path
    manifest: WallpaperManifest
    theme_source: str


class ReadinessService:
    """Non-mutating diagnostics plus safe generation of local visual assets."""

    def __init__(
        self,
        base_path: Path | str | None = None,
        photo_config: PhotoSourceConfig | None = None,
        theme_plan: ThemePlan | None = None,
    ) -> None:
        self.base_path = Path(base_path) if base_path is not None else None
        self.photo_config = photo_config or PhotoSourceConfig()
        self.theme_plan = theme_plan
        self.planner = WallpaperApplyPlanner(
            base_path=self.base_path,
            photo_config=self.photo_config,
        )

    def doctor_lines(self) -> tuple[str, ...]:
        failures: list[str] = []
        app_root = get_chaseos_data_dir(self.base_path)
        windows = platform.system().lower() == "windows"
        pyside = _import_status("PySide6")
        pillow = _import_status("PIL")
        comtypes = _import_status("comtypes")
        wallpaper_api = self._wallpaper_api_status()
        public_poster_status = _exists_status(
            self.planner.latest_approved_public_poster(),
            warn="missing",
        )
        rollback_status = _exists_status(
            get_previous_wallpapers_path(self.base_path),
            warn="missing",
        )
        diagnostics_status = _exists_status(
            get_last_wallpaper_diagnostics_path(self.base_path),
            warn="missing",
        )
        smoke_status = _exists_status(
            get_last_wallpaper_smoke_json_path(self.base_path),
            warn="missing",
        )
        if not pyside:
            failures.append("PySide6 import failed")
        if not pillow:
            failures.append("Pillow import failed")
        if windows and not comtypes:
            failures.append("comtypes import failed")

        title = "CHASEOS // DOCTOR FAILED" if failures else "CHASEOS // DOCTOR"
        lines = [
            title,
            "",
            "Environment",
            f"  App: ChaseOS {__version__}",
            f"  Python: {sys.version.split()[0]}",
            f"  Platform: {platform.platform()}",
            f"  Windows: {_status(windows)}",
            f"  PySide6: {_status(pyside)}",
            f"  Pillow: {_status(pillow)}",
            f"  comtypes: {_status(comtypes, fail_on_false=windows)}",
            f"  Windows wallpaper API: {wallpaper_api}",
            "",
            "Runtime paths",
            f"  App data: {app_root}",
            f"  Config: {_directory_status(get_config_dir(self.base_path))}",
            f"  Posters: {_directory_status(app_root / 'posters')}",
            f"  Generated: {_directory_status(app_root / 'generated')}",
            f"  Wallpaper state: {_directory_status(get_wallpaper_state_dir(self.base_path))}",
            "",
            "Wallpaper readiness",
            f"  Monitor mapping: {_exists_status(get_monitor_mapping_path(self.base_path))}",
            f"  Display 1 art: {public_poster_status}",
            f"  Generated manifest: {_exists_status(_manifest_path(self.planner), warn='missing')}",
            f"  Rollback state: {rollback_status}",
            f"  Last diagnostics: {diagnostics_status}",
            f"  Last smoke report: {smoke_status}",
        ]
        lines.extend(f"FAIL {failure}" for failure in failures)
        lines.append("")
        lines.append("No wallpaper changes applied.")
        return tuple(lines)

    def assets_status_lines(self) -> tuple[str, ...]:
        manifest = self.planner.latest_wallpaper_manifest()
        poster_path = self.planner.latest_approved_public_poster()
        lines = ["CHASEOS // ASSETS STATUS", ""]
        if manifest is None:
            lines.extend(
                (
                    "No generated wallpaper manifest found.",
                    (
                        "Run /prepare wallpapers --takeaway-file <path> to create a safe "
                        "daily asset set without applying wallpapers."
                    ),
                    "No wallpaper changes applied.",
                )
            )
            return tuple(lines)

        lines.extend(
            (
                f"Latest Display 1 art: {poster_path if poster_path else 'missing'}",
                f"Display 1 art dimensions: {_dimensions_label(poster_path)}",
                f"Latest wallpaper manifest: {manifest.manifest_path}",
                f"Generated date: {manifest.date.isoformat()}",
                "",
            )
        )
        candidates = [
            ("Display 1 public", manifest.public_poster_path),
            ("Display 4 left atmosphere", _wallpaper_path(manifest, "display_4")),
            ("Display 2 center command", _wallpaper_path(manifest, "display_2")),
            ("Display 3 right inspiration", _wallpaper_path(manifest, "display_3")),
        ]
        for label, path in candidates:
            lines.extend(
                (
                    label,
                    f"  Path: {path if path else 'missing'}",
                    f"  Exists: {'yes' if path and path.exists() else 'no'}",
                    f"  Readable image: {'yes' if _image_dimensions(path)[0] else 'no'}",
                    f"  Dimensions: {_dimensions_label(path)}",
                )
            )
            if label.startswith("Display 1"):
                unsafe = bool(path and self.planner._is_general_photo_path(path))
                lines.append(f"  Public-only safe: {'no' if unsafe else 'yes'}")
                if unsafe:
                    lines.append("  WARN Display 1 candidate appears to come from general photos")
            lines.append("")
        lines.append("No wallpaper changes applied.")
        return tuple(lines)

    def prepare_wallpapers_lines(self, argument: str) -> tuple[str, ...]:
        try:
            takeaway, source, warnings = self._takeaway_from_argument(argument)
        except ValueError as exc:
            return (
                "CHASEOS // PREPARE WALLPAPERS FAILED",
                "",
                str(exc),
                "Use /prepare wallpapers --takeaway-file <path>",
                "or /prepare wallpapers --takeaway <text>",
                "",
                "No wallpaper assets generated.",
                "No desktop wallpaper changes applied.",
            )

        theme, theme_source = self._theme_plan()
        poster_engine = Display1ArtEngine(base_path=self.base_path)
        plan = poster_engine.build_plan(
            innovation_exercise="First-run readiness",
            private_innovation_takeaway=takeaway,
            theme_plan=theme,
            raw_check_in=None,
        )
        poster_result = poster_engine.render(
            plan=plan,
            innovation_exercise="First-run readiness",
            private_innovation_takeaway=takeaway,
            theme_plan=theme,
            approved=True,
            force_regenerate=True,
        )
        manifest = WallpaperComposer(
            base_path=self.base_path,
            photo_config=self.photo_config,
        ).generate(
            theme_plan=theme,
            public_poster_path=poster_result.image_path,
            regenerate_count=0,
        )
        lines = [
            "CHASEOS // PREPARE WALLPAPERS",
            "",
            *warnings,
            f"Innovation takeaway source: {source}",
            f"Theme source: {theme_source}",
            f"Display 1 art: {poster_result.image_path}",
            f"Display 1 art metadata: {poster_result.metadata_path}",
            f"Display 4 wallpaper: {manifest.wallpapers['display_4'].image_path}",
            f"Display 2 wallpaper: {manifest.wallpapers['display_2'].image_path}",
            f"Display 3 wallpaper: {manifest.wallpapers['display_3'].image_path}",
            f"Wallpaper manifest: {manifest.manifest_path}",
            "",
            "Wallpapers were generated only.",
            "No desktop wallpaper changes applied.",
        ]
        return tuple(line for line in lines if line)

    def _takeaway_from_argument(self, argument: str) -> tuple[str, str, tuple[str, ...]]:
        parts = shlex.split(argument, posix=False)
        file_path: Path | None = None
        text_parts: list[str] = []
        index = 0
        while index < len(parts):
            token = parts[index]
            if token == "--takeaway-file" and index + 1 < len(parts):
                file_path = Path(parts[index + 1])
                index += 2
                continue
            if token == "--takeaway" and index + 1 < len(parts):
                text_parts.append(parts[index + 1])
                index += 2
                continue
            index += 1

        warnings = []
        if file_path is not None:
            if text_parts:
                warnings.append("WARN both file and text provided; using takeaway file.")
            if not file_path.exists():
                raise ValueError(f"Innovation takeaway file not found: {file_path}")
            takeaway = file_path.read_text(encoding="utf-8").strip()
            source = str(file_path)
        else:
            takeaway = " ".join(text_parts).strip()
            source = "inline text"

        if not takeaway:
            raise ValueError("Innovation takeaway is required for the public poster.")
        return takeaway, source, tuple(warnings)

    def _theme_plan(self) -> tuple[ThemePlan, str]:
        if self.theme_plan is not None:
            return self.theme_plan, "latest approved/current theme plan"
        result = ThemeGenerator().generate(
            signals=PracticalSignals(),
            startup_mode=StartupMode.STRUCTURED,
            change_requests=("more minimal", "less visual noise"),
        )
        return result.plan, "fallback baseline theme"

    def _wallpaper_api_status(self) -> str:
        if platform.system().lower() != "windows":
            return "WARN non-Windows"
        try:
            WindowsDesktopWallpaper().list_monitors()
        except (DesktopWallpaperError, AttributeError, OSError, RuntimeError) as exc:
            return f"FAIL {exc}"
        return "PASS"


def _import_status(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _status(value: bool, fail_on_false: bool = True) -> str:
    if value:
        return "PASS"
    return "FAIL" if fail_on_false else "WARN"


def _directory_status(path: Path) -> str:
    if not path.exists():
        return "WARN missing"
    if not path.is_dir():
        return "FAIL not a directory"
    try:
        probe = path / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return f"FAIL not writable: {exc}"
    return "PASS"


def _exists_status(path: Path | None, warn: str = "missing") -> str:
    if path is not None and path.exists():
        return "PASS"
    return f"WARN {warn}"


def _manifest_path(planner: WallpaperApplyPlanner) -> Path | None:
    manifest = planner.latest_wallpaper_manifest()
    return manifest.manifest_path if manifest else None


def _wallpaper_path(manifest: WallpaperManifest, key: str) -> Path | None:
    wallpaper = manifest.wallpapers.get(key)
    return wallpaper.image_path if wallpaper else None


def _dimensions_label(path: Path | None) -> str:
    width, height = _image_dimensions(path)
    return f"{width}x{height}" if width and height else "unavailable"


def _image_dimensions(path: Path | None) -> tuple[int | None, int | None]:
    if path is None or not path.exists():
        return None, None
    try:
        with Image.open(path) as image:
            image.verify()
            return image.size
    except (OSError, UnidentifiedImageError):
        return None, None
