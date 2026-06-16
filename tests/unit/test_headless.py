from __future__ import annotations

import json
from io import StringIO

import pytest

from chaseos.__main__ import main
from chaseos.app.headless import (
    EXIT_BLOCKED,
    EXIT_FAILURE,
    EXIT_SUCCESS,
    HeadlessCommandRun,
    HeadlessCommandRunner,
    run_headless_cli,
)
from chaseos.ritual.startup_sequence import StartupSequence
from chaseos.storage.paths import (
    get_last_startup_smoke_json_path,
    get_last_startup_smoke_text_path,
    get_last_wallpaper_smoke_json_path,
    get_last_wallpaper_smoke_text_path,
)
from chaseos.wallpaper.applier import WallpaperApplier
from chaseos.wallpaper.windows_desktop_wallpaper import DesktopWallpaperMonitor


@pytest.fixture(autouse=True)
def use_fallback_monitor_detection(monkeypatch) -> None:
    monkeypatch.setattr("chaseos.windows.display_detection.detect_monitors", lambda: [])


class FakeDesktopWallpaper:
    def __init__(self) -> None:
        self.set_calls: list[tuple[str, str]] = []

    def list_monitors(self) -> tuple[str, ...]:
        return tuple(monitor.monitor_id for monitor in self.describe_monitors())

    def describe_monitors(self) -> tuple[DesktopWallpaperMonitor, ...]:
        return (
            DesktopWallpaperMonitor(0, "fallback_display_1", None, 0, 0, 1080, 1920),
            DesktopWallpaperMonitor(1, "fallback_display_4", None, 1080, 0, 3000, 1080),
            DesktopWallpaperMonitor(2, "fallback_display_2", None, 3000, 0, 4920, 1080),
            DesktopWallpaperMonitor(3, "fallback_display_3", None, 4920, 0, 6840, 1080),
        )

    def get_wallpaper(self, monitor_id: str) -> str | None:
        return None

    def set_wallpaper(self, monitor_id: str, image_path: str) -> None:
        self.set_calls.append((monitor_id, image_path))


def startup_smoke_sequence(tmp_path, fake: FakeDesktopWallpaper) -> StartupSequence:
    return StartupSequence(
        data_dir=tmp_path,
        wallpaper_applier=WallpaperApplier(client=fake, base_path=tmp_path),
    )


def test_python_m_chaseos_with_no_args_selects_normal_gui_launch_path(monkeypatch) -> None:
    called = {}
    monkeypatch.setattr("sys.argv", ["chaseos"])

    def fake_tray_run(argv):
        called["argv"] = argv
        return 42

    assert main([], tray_run=fake_tray_run) == 42
    assert called["argv"] == ["chaseos"]


def test_command_runs_safe_command_through_router() -> None:
    stdout = StringIO()

    exit_code = run_headless_cli(["--command", "/version"], stdout=stdout)

    assert exit_code == EXIT_SUCCESS
    assert "CHASEOS // VERSION" in stdout.getvalue()


def test_c_alias_runs_safe_command() -> None:
    stdout = StringIO()

    exit_code = run_headless_cli(["-c", "/version"], stdout=stdout)

    assert exit_code == EXIT_SUCCESS
    assert "app: ChaseOS" in stdout.getvalue()


def test_command_prints_output_to_stdout() -> None:
    stdout = StringIO()

    run_headless_cli(["--command", "/help"], stdout=stdout)

    assert "available commands:" in stdout.getvalue()


def test_command_returns_nonzero_for_validation_failure(tmp_path) -> None:
    stdout = StringIO()

    exit_code = run_headless_cli(
        ["--command", "/verify wallpapers"],
        stdout=stdout,
        base_path=tmp_path,
    )

    assert exit_code == EXIT_FAILURE
    assert "PREFLIGHT FAILED" in stdout.getvalue()


def test_headless_apply_wallpapers_dry_run_is_allowed_without_unlock(tmp_path) -> None:
    stdout = StringIO()

    exit_code = run_headless_cli(
        ["--command", "/apply wallpapers --dry-run"],
        stdout=stdout,
        base_path=tmp_path,
    )

    assert exit_code == EXIT_FAILURE
    assert "COMMAND BLOCKED" not in stdout.getvalue()


def test_headless_apply_confirm_is_blocked_without_unlock() -> None:
    stdout = StringIO()

    exit_code = run_headless_cli(
        ["--command", "/apply wallpapers --confirm"],
        stdout=stdout,
    )

    assert exit_code == EXIT_BLOCKED
    assert "CHASEOS // COMMAND BLOCKED" in stdout.getvalue()


def test_headless_reset_wallpapers_is_blocked_without_unlock() -> None:
    stdout = StringIO()

    exit_code = run_headless_cli(["--command", "/reset wallpapers"], stdout=stdout)

    assert exit_code == EXIT_BLOCKED
    assert "No changes applied." in stdout.getvalue()


def test_headless_apply_confirm_reaches_applier_with_unlock(tmp_path) -> None:
    stdout = StringIO()

    exit_code = run_headless_cli(
        [
            "--command",
            "/apply wallpapers --confirm",
            "--allow-desktop-changes",
        ],
        stdout=stdout,
        base_path=tmp_path,
    )

    assert exit_code == EXIT_FAILURE
    assert "COMMAND BLOCKED" not in stdout.getvalue()


def test_script_ignores_blank_lines_and_comments(tmp_path) -> None:
    script = tmp_path / "smoke.txt"
    script.write_text("\n# comment\n/version\n\n", encoding="utf-8")
    stdout = StringIO()

    exit_code = run_headless_cli(["--script", str(script)], stdout=stdout)

    assert exit_code == EXIT_SUCCESS
    assert stdout.getvalue().count("CHASEOS // COMMAND:") == 1


def test_script_runs_commands_in_order(tmp_path) -> None:
    script = tmp_path / "script.txt"
    script.write_text("/version\n/help\n", encoding="utf-8")
    stdout = StringIO()

    run_headless_cli(["--script", str(script)], stdout=stdout)
    output = stdout.getvalue()

    assert output.index("CHASEOS // COMMAND: /version") < output.index(
        "CHASEOS // COMMAND: /help"
    )


def test_script_returns_nonzero_if_any_command_fails(tmp_path) -> None:
    script = tmp_path / "script.txt"
    script.write_text("/version\n/verify wallpapers\n", encoding="utf-8")
    stdout = StringIO()

    exit_code = run_headless_cli(["--script", str(script)], stdout=stdout, base_path=tmp_path)

    assert exit_code == EXIT_FAILURE


class RecordingRunner(HeadlessCommandRunner):
    def __init__(self) -> None:
        self.commands: list[str] = []

    def run_commands(self, commands):
        self.commands.extend(commands)
        return tuple(
            HeadlessCommandRun(command=command, output=("ok",), exit_code=0, status="passed")
            for command in commands
        )


def test_smoke_wallpapers_runs_exact_non_mutating_commands() -> None:
    runner = HeadlessCommandRunner()
    runs = runner.run_commands((
        "/wallpaper status",
        "/wallpaper diagnostics",
        "/verify wallpapers",
        "/apply wallpapers --dry-run",
    ))

    assert [run.command for run in runs] == [
        "/wallpaper status",
        "/wallpaper diagnostics",
        "/verify wallpapers",
        "/apply wallpapers --dry-run",
    ]
    assert "/apply wallpapers --confirm" not in [run.command for run in runs]
    assert "/reset wallpapers" not in [run.command for run in runs]


def test_smoke_wallpapers_writes_text_and_json_reports(tmp_path) -> None:
    stdout = StringIO()

    run_headless_cli(["--smoke", "wallpapers"], stdout=stdout, base_path=tmp_path)

    assert get_last_wallpaper_smoke_text_path(tmp_path).exists()
    assert get_last_wallpaper_smoke_json_path(tmp_path).exists()


def test_smoke_report_still_writes_when_verify_fails(tmp_path) -> None:
    stdout = StringIO()

    exit_code = run_headless_cli(["--smoke", "wallpapers"], stdout=stdout, base_path=tmp_path)

    payload = json.loads(get_last_wallpaper_smoke_json_path(tmp_path).read_text(encoding="utf-8"))
    assert exit_code == EXIT_FAILURE
    assert payload["aggregate_status"] == "failed"
    assert payload["exit_code"] == EXIT_FAILURE


def test_smoke_wallpapers_json_includes_exact_commands(tmp_path) -> None:
    stdout = StringIO()

    run_headless_cli(["--smoke", "wallpapers"], stdout=stdout, base_path=tmp_path)

    payload = json.loads(get_last_wallpaper_smoke_json_path(tmp_path).read_text(encoding="utf-8"))
    assert payload["commands"] == [
        "/wallpaper status",
        "/wallpaper diagnostics",
        "/verify wallpapers",
        "/apply wallpapers --dry-run",
    ]


def test_command_daily_status_runs_headless(tmp_path) -> None:
    stdout = StringIO()

    exit_code = run_headless_cli(["--command", "/daily status"], stdout=stdout, base_path=tmp_path)

    assert exit_code == EXIT_SUCCESS
    assert "No daily startup session found for today." in stdout.getvalue()


def test_smoke_startup_runs_non_mutating_end_to_end(tmp_path) -> None:
    stdout = StringIO()
    fake = FakeDesktopWallpaper()
    sequence = startup_smoke_sequence(tmp_path, fake)

    exit_code = run_headless_cli(
        ["--smoke", "startup"],
        stdout=stdout,
        sequence=sequence,
        base_path=tmp_path,
    )
    output = stdout.getvalue()

    assert exit_code == EXIT_SUCCESS
    assert "Daily assets are ready." in output
    assert fake.set_calls == []


def test_smoke_startup_writes_text_and_json_reports(tmp_path) -> None:
    stdout = StringIO()

    run_headless_cli(
        ["--smoke", "startup"],
        stdout=stdout,
        sequence=startup_smoke_sequence(tmp_path, FakeDesktopWallpaper()),
        base_path=tmp_path,
    )

    assert get_last_startup_smoke_text_path(tmp_path).exists()
    assert get_last_startup_smoke_json_path(tmp_path).exists()


def test_smoke_startup_json_is_non_mutating_and_marks_test_data(tmp_path) -> None:
    stdout = StringIO()

    run_headless_cli(
        ["--smoke", "startup"],
        stdout=stdout,
        sequence=startup_smoke_sequence(tmp_path, FakeDesktopWallpaper()),
        base_path=tmp_path,
    )

    payload = json.loads(get_last_startup_smoke_json_path(tmp_path).read_text(encoding="utf-8"))
    assert payload["test_data"] is True
    assert "/apply wallpapers --confirm" not in payload["commands_or_inputs"]
    assert "/reset wallpapers" not in payload["commands_or_inputs"]
    assert payload["generated_asset_paths"]
