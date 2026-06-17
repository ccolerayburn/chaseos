"""Release metadata reporting for ChaseOS."""

from __future__ import annotations

import importlib.metadata
import platform
import subprocess
import sys
from pathlib import Path

from chaseos import __version__
from chaseos.storage.paths import get_chaseos_data_dir


class ReleaseInfoService:
    def __init__(
        self,
        project_root: Path | str | None = None,
        base_path: Path | str | None = None,
    ) -> None:
        self.project_root = Path(project_root) if project_root is not None else Path.cwd()
        self.base_path = Path(base_path) if base_path is not None else None

    def lines(self) -> tuple[str, ...]:
        commit, dirty = self._git_info()
        return (
            "CHASEOS // RELEASE INFO",
            "",
            "Application",
            "  app: ChaseOS",
            f"  version: {__version__}",
            f"  python: {sys.version.split()[0]}",
            f"  platform: {platform.platform()}",
            f"  project root: {self.project_root}",
            f"  app data root: {get_chaseos_data_dir(self.base_path)}",
            f"  git commit: {commit}",
            f"  dirty working tree: {dirty}",
            "",
            "Dependencies",
            f"  PySide6: {_package_version('PySide6')}",
            f"  Pillow: {_package_version('Pillow')}",
            f"  comtypes: {_comtypes_version()}",
            "",
            "Launch modes",
            "  GUI tray",
            "  headless command",
            "  script",
            "  smoke wallpapers",
            "  smoke startup",
            "  smoke release",
            "",
            "Safety",
            "  wallpaper apply explicit only",
            "  startup shortcut per-user only",
            "  no registry startup keys",
            "  no admin required",
            "No wallpaper changes applied.",
        )

    def _git_info(self) -> tuple[str, str]:
        try:
            commit = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=self.project_root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        except (subprocess.SubprocessError, OSError):
            return "unknown", "unknown"
        return commit or "unknown", "yes" if status else "no"


def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "missing"


def _comtypes_version() -> str:
    if platform.system() != "Windows":
        return "n/a"
    return _package_version("comtypes")
