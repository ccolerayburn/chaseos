"""Per-user Windows shortcut management for ChaseOS."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SHORTCUT_NAME = "ChaseOS.lnk"
STARTUP_FOLDER_RELATIVE = ("Microsoft", "Windows", "Start Menu", "Programs", "Startup")
START_MENU_PROGRAMS_RELATIVE = ("Microsoft", "Windows", "Start Menu", "Programs")
DESKTOP_RELATIVE = ("Desktop",)


@dataclass(frozen=True)
class StartupShortcutInfo:
    exists: bool
    path: Path
    target: str | None = None
    arguments: str | None = None
    working_directory: str | None = None
    icon_location: str | None = None


class PowerShellShortcutBackend:
    """Create and inspect .lnk files via Windows Script Host COM from PowerShell."""

    def status(self, shortcut_path: Path) -> StartupShortcutInfo:
        if not shortcut_path.exists():
            return StartupShortcutInfo(exists=False, path=shortcut_path)
        script = (
            "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($args[0]);"
            "$o=[ordered]@{target=$s.TargetPath;arguments=$s.Arguments;"
            "working_directory=$s.WorkingDirectory;icon_location=$s.IconLocation};"
            "$o|ConvertTo-Json -Compress"
        )
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", script, str(shortcut_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout)
        except (subprocess.SubprocessError, ValueError, OSError):
            payload = {}
        return StartupShortcutInfo(
            exists=True,
            path=shortcut_path,
            target=payload.get("target"),
            arguments=payload.get("arguments"),
            working_directory=payload.get("working_directory"),
            icon_location=payload.get("icon_location"),
        )

    def create_or_update(
        self,
        shortcut_path: Path,
        target: Path,
        arguments: str,
        working_directory: Path,
        icon_path: Path | None = None,
    ) -> None:
        shortcut_path.parent.mkdir(parents=True, exist_ok=True)
        script = (
            "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($args[0]);"
            "$s.TargetPath=$args[1];$s.Arguments=$args[2];"
            "$s.WorkingDirectory=$args[3];"
            "if ($args[4]) {$s.IconLocation=$args[4]};$s.Save()"
        )
        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                script,
                str(shortcut_path),
                str(target),
                arguments,
                str(working_directory),
                str(icon_path or ""),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    def remove(self, shortcut_path: Path) -> bool:
        if not shortcut_path.exists():
            return False
        shortcut_path.unlink()
        return True


class StartupShortcutManager:
    """Manage ChaseOS per-user Startup and Start Menu shortcuts."""

    def __init__(
        self,
        project_root: Path | str | None = None,
        backend: PowerShellShortcutBackend | None = None,
        startup_folder: Path | str | None = None,
        start_menu_folder: Path | str | None = None,
        desktop_folder: Path | str | None = None,
    ) -> None:
        self.project_root = Path(project_root) if project_root is not None else Path.cwd()
        self.backend = backend or PowerShellShortcutBackend()
        self.startup_folder = Path(startup_folder) if startup_folder else _startup_folder()
        self.start_menu_folder = (
            Path(start_menu_folder) if start_menu_folder else _start_menu_programs_folder()
        )
        self.desktop_folder = Path(desktop_folder) if desktop_folder else _desktop_folder()
        self.shortcut_path = self.startup_folder / SHORTCUT_NAME
        self.start_menu_shortcut_path = self.start_menu_folder / SHORTCUT_NAME
        self.desktop_shortcut_path = self.desktop_folder / SHORTCUT_NAME

    def status_lines(self) -> tuple[str, ...]:
        info = self.backend.status(self.shortcut_path)
        return (
            "CHASEOS // STARTUP STATUS",
            f"shortcut exists: {'yes' if info.exists else 'no'}",
            f"shortcut path: {info.path}",
            f"target: {info.target or 'n/a'}",
            f"arguments: {info.arguments or 'n/a'}",
            f"working directory: {info.working_directory or 'n/a'}",
            "startup scope: current user Startup folder only",
            "registry Run keys: not used",
            "scheduled tasks: not used",
            "No wallpaper changes applied.",
        )

    def enable_lines(self) -> tuple[str, ...]:
        target = _pythonw_or_python()
        arguments = "-m chaseos"
        self.backend.create_or_update(
            self.shortcut_path,
            target=target,
            arguments=arguments,
            working_directory=self.project_root,
            icon_path=_icon_path(),
        )
        return (
            "CHASEOS // STARTUP ENABLED",
            "shortcut created/updated.",
            f"shortcut path: {self.shortcut_path}",
            f"target: {target}",
            f"arguments: {arguments}",
            f"working directory: {self.project_root}",
            "startup scope: current user Startup folder only",
            "registry Run keys: not used",
            "scheduled tasks: not used",
            "No wallpaper changes applied.",
        )

    def disable_lines(self) -> tuple[str, ...]:
        removed = self.backend.remove(self.shortcut_path)
        return (
            "CHASEOS // STARTUP DISABLED",
            f"shortcut removed: {'yes' if removed else 'no'}",
            f"shortcut path: {self.shortcut_path}",
            "startup scope: current user Startup folder only",
            "registry Run keys: not used",
            "scheduled tasks: not used",
            "No wallpaper changes applied.",
        )

    def install_shortcut_lines(self) -> tuple[str, ...]:
        target = _gui_chaseos_exe()
        icon_path = _icon_path()
        self.backend.create_or_update(
            self.start_menu_shortcut_path,
            target=target,
            arguments="",
            working_directory=self.project_root,
            icon_path=icon_path,
        )
        return (
            "CHASEOS // SHORTCUT INSTALLED",
            "Start Menu shortcut created/updated.",
            f"shortcut path: {self.start_menu_shortcut_path}",
            f"target: {target}",
            f"icon: {icon_path}",
            f"working directory: {self.project_root}",
            "To pin: open Start, right-click ChaseOS, then choose Pin to taskbar.",
            "Windows does not provide a supported taskbar pinning API.",
            "Startup auto-launch was not enabled.",
            "No wallpaper changes applied.",
        )

    def uninstall_shortcut_lines(self) -> tuple[str, ...]:
        removed = self.backend.remove(self.start_menu_shortcut_path)
        return (
            "CHASEOS // SHORTCUT UNINSTALLED",
            f"shortcut removed: {'yes' if removed else 'no'}",
            f"shortcut path: {self.start_menu_shortcut_path}",
            "Startup shortcut was not changed.",
            "No wallpaper changes applied.",
        )


def _startup_folder() -> Path:
    return _roaming_path(STARTUP_FOLDER_RELATIVE)


def _start_menu_programs_folder() -> Path:
    return _roaming_path(START_MENU_PROGRAMS_RELATIVE)


def _desktop_folder() -> Path:
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        return Path(user_profile).joinpath(*DESKTOP_RELATIVE)
    return Path.home().joinpath(*DESKTOP_RELATIVE)


def _roaming_path(parts: tuple[str, ...]) -> Path:
    app_data = os.environ.get("APPDATA")
    if app_data:
        return Path(app_data).joinpath(*parts)
    return Path.home().joinpath("AppData", "Roaming", *parts)


def _pythonw_or_python() -> Path:
    executable = Path(sys.executable)
    pythonw = executable.with_name("pythonw.exe")
    return pythonw if pythonw.exists() else executable


def _gui_chaseos_exe() -> Path:
    executable = Path(sys.executable)
    candidate = executable.with_name("chaseos.exe")
    return candidate if candidate.exists() else executable


def _icon_path() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "chaseos.ico"
