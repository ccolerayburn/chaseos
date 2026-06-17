from __future__ import annotations

import json
from pathlib import Path

from chaseos.app.release_info import ReleaseInfoService
from chaseos.app.tray_app import SAFE_TRAY_ACTIONS
from chaseos.ritual.startup_sequence import StartupSequence
from chaseos.windows.single_instance import SingleInstanceGuard
from chaseos.windows.startup_shortcut import StartupShortcutInfo, StartupShortcutManager


class FakeShortcutBackend:
    def __init__(self) -> None:
        self.info: StartupShortcutInfo | None = None
        self.created: tuple[Path, Path, str, Path, Path | None] | None = None
        self.removed: Path | None = None

    def status(self, shortcut_path: Path) -> StartupShortcutInfo:
        return self.info or StartupShortcutInfo(exists=False, path=shortcut_path)

    def create_or_update(
        self,
        shortcut_path: Path,
        target: Path,
        arguments: str,
        working_directory: Path,
        icon_path: Path | None = None,
    ) -> None:
        self.created = (shortcut_path, target, arguments, working_directory, icon_path)
        self.info = StartupShortcutInfo(
            exists=True,
            path=shortcut_path,
            target=str(target),
            arguments=arguments,
            working_directory=str(working_directory),
            icon_location=str(icon_path) if icon_path else None,
        )

    def remove(self, shortcut_path: Path) -> bool:
        self.removed = shortcut_path
        existed = bool(self.info and self.info.exists)
        self.info = StartupShortcutInfo(exists=False, path=shortcut_path)
        return existed


def test_second_gui_launch_is_blocked_by_single_instance_guard(tmp_path) -> None:
    first = SingleInstanceGuard(base_path=tmp_path)
    second = SingleInstanceGuard(base_path=tmp_path)

    assert first.acquire() is True
    assert second.acquire() is False
    first.release()


def test_stale_lock_is_handled(tmp_path) -> None:
    guard = SingleInstanceGuard(base_path=tmp_path)
    guard.path.parent.mkdir(parents=True)
    guard.path.write_text(json.dumps({"pid": 999999999}), encoding="utf-8")

    assert guard.acquire() is True
    guard.release()


def test_headless_main_path_does_not_use_single_instance_guard(monkeypatch) -> None:
    from chaseos.__main__ import main

    called = {}

    def fake_headless(argv):
        called["argv"] = argv
        return 0

    monkeypatch.setattr("chaseos.__main__.run_headless_cli", fake_headless)

    assert main(["--command", "/version"]) == 0
    assert called["argv"] == ["--command", "/version"]


def test_tray_menu_safe_expected_actions_only() -> None:
    labels = [label for label, _command in SAFE_TRAY_ACTIONS]
    commands = [command for _label, command in SAFE_TRAY_ACTIONS if command]

    assert labels == [
        "Open ChaseOS",
        "Start daily ritual",
        "Daily status",
        "Wallpaper dry-run",
        "Wallpaper status",
        "Help",
        "Quit",
    ]
    assert "/apply wallpapers --confirm" not in commands
    assert "/reset wallpapers" not in commands


def test_startup_status_reports_missing_shortcut(tmp_path) -> None:
    manager = StartupShortcutManager(
        project_root=tmp_path,
        backend=FakeShortcutBackend(),
        startup_folder=tmp_path / "startup",
    )

    text = "\n".join(manager.status_lines())

    assert "shortcut exists: no" in text
    assert "registry Run keys: not used" in text


def test_startup_enable_creates_shortcut_through_backend(tmp_path) -> None:
    backend = FakeShortcutBackend()
    manager = StartupShortcutManager(
        project_root=tmp_path,
        backend=backend,
        startup_folder=tmp_path / "startup",
    )

    text = "\n".join(manager.enable_lines())

    assert backend.created is not None
    assert backend.created[2] == "-m chaseos"
    assert backend.created[3] == tmp_path
    assert "shortcut created/updated." in text
    assert "registry Run keys: not used" in text


def test_startup_disable_removes_shortcut_through_backend(tmp_path) -> None:
    backend = FakeShortcutBackend()
    manager = StartupShortcutManager(
        project_root=tmp_path,
        backend=backend,
        startup_folder=tmp_path / "startup",
    )
    manager.enable_lines()

    text = "\n".join(manager.disable_lines())

    assert backend.removed == manager.shortcut_path
    assert "shortcut removed: yes" in text
    assert "registry Run keys: not used" in text


def test_install_shortcut_creates_start_menu_shortcut_without_startup(tmp_path) -> None:
    backend = FakeShortcutBackend()
    manager = StartupShortcutManager(
        project_root=tmp_path,
        backend=backend,
        startup_folder=tmp_path / "startup",
        start_menu_folder=tmp_path / "programs",
    )

    text = "\n".join(manager.install_shortcut_lines())

    assert backend.created is not None
    assert backend.created[0] == tmp_path / "programs" / "ChaseOS.lnk"
    assert backend.created[2] == ""
    assert backend.created[3] == tmp_path
    assert backend.created[4] is not None
    assert "Pin to taskbar" in text
    assert "Startup auto-launch was not enabled." in text


def test_uninstall_shortcut_removes_start_menu_shortcut_only(tmp_path) -> None:
    backend = FakeShortcutBackend()
    manager = StartupShortcutManager(
        project_root=tmp_path,
        backend=backend,
        startup_folder=tmp_path / "startup",
        start_menu_folder=tmp_path / "programs",
    )
    manager.install_shortcut_lines()

    text = "\n".join(manager.uninstall_shortcut_lines())

    assert backend.removed == manager.start_menu_shortcut_path
    assert "Startup shortcut was not changed." in text


def test_startup_commands_are_routed_without_registry_backend(tmp_path) -> None:
    sequence = StartupSequence(data_dir=tmp_path)
    backend = FakeShortcutBackend()
    sequence.startup_shortcuts = StartupShortcutManager(
        project_root=tmp_path,
        backend=backend,
        startup_folder=tmp_path / "startup",
    )

    status = sequence.handle_input("/startup status")
    enable = sequence.handle_input("/startup enable")
    disable = sequence.handle_input("/startup disable")
    text = "\n".join(line.text for line in (*status.lines, *enable.lines, *disable.lines))

    assert backend.created is not None
    assert backend.removed == sequence.startup_shortcuts.shortcut_path
    assert "registry Run keys: not used" in text


def test_install_shortcut_commands_are_routed_without_registry_backend(tmp_path) -> None:
    sequence = StartupSequence(data_dir=tmp_path)
    backend = FakeShortcutBackend()
    sequence.startup_shortcuts = StartupShortcutManager(
        project_root=tmp_path,
        backend=backend,
        startup_folder=tmp_path / "startup",
        start_menu_folder=tmp_path / "programs",
    )

    install = sequence.handle_input("/install shortcut")
    uninstall = sequence.handle_input("/uninstall shortcut")
    text = "\n".join(line.text for line in (*install.lines, *uninstall.lines))

    assert backend.created is not None
    assert backend.removed == sequence.startup_shortcuts.start_menu_shortcut_path
    assert "SHORTCUT INSTALLED" in text
    assert "SHORTCUT UNINSTALLED" in text


def test_release_info_includes_metadata_sections(tmp_path) -> None:
    text = "\n".join(ReleaseInfoService(project_root=tmp_path, base_path=tmp_path).lines())

    assert "CHASEOS // RELEASE INFO" in text
    assert "Application" in text
    assert "Dependencies" in text
    assert "Launch modes" in text
    assert "Safety" in text


def test_release_info_handles_missing_git_gracefully(tmp_path, monkeypatch) -> None:
    def fake_run(*_args, **_kwargs):
        raise OSError("git missing")

    monkeypatch.setattr("subprocess.run", fake_run)

    text = "\n".join(ReleaseInfoService(project_root=tmp_path, base_path=tmp_path).lines())

    assert "git commit: unknown" in text
    assert "dirty working tree: unknown" in text
