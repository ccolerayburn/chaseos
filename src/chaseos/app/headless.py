"""Headless command execution for ChaseOS."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from chaseos.app.command_router import CommandResult, TerminalLine, route_command
from chaseos.ritual.startup_sequence import StartupSequence
from chaseos.storage.paths import (
    get_last_release_smoke_json_path,
    get_last_release_smoke_text_path,
    get_last_startup_smoke_json_path,
    get_last_startup_smoke_text_path,
    get_last_wallpaper_smoke_json_path,
    get_last_wallpaper_smoke_text_path,
)

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2
EXIT_BLOCKED = 3

WALLPAPER_SMOKE_COMMANDS = (
    "/wallpaper status",
    "/wallpaper diagnostics",
    "/verify wallpapers",
    "/apply wallpapers --dry-run",
)

STARTUP_SMOKE_INPUTS = (
    "/start",
    "smoke test: clear calm focused rested and ready for a structured start",
    "/approve",
    "done",
    "done",
    "A small visible improvement beats a hidden perfect plan.",
    "/takeaway A small visible improvement beats a hidden perfect plan.",
    "/approve",
    "done",
)

RELEASE_SMOKE_COMMANDS = (
    "/version",
    "/doctor",
    "/release info",
    "/startup status",
    "/daily status",
    "/assets status",
    "/wallpaper status",
    "/verify wallpapers",
    "/apply wallpapers --dry-run",
    "/export support --dry-run",
)

MUTATING_COMMANDS = (
    "/apply wallpapers --confirm",
    "/reset wallpapers",
)


@dataclass(frozen=True)
class HeadlessCommandRun:
    command: str
    output: tuple[str, ...]
    exit_code: int
    status: str


def run_headless_cli(
    argv: Sequence[str],
    stdout: TextIO | None = None,
    sequence: StartupSequence | None = None,
    base_path: Path | str | None = None,
) -> int:
    """Parse and run ChaseOS headless CLI arguments."""

    stdout = stdout or sys.stdout
    parser = _build_parser()
    try:
        args = parser.parse_args(list(argv))
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else EXIT_USAGE

    selected = sum(bool(value) for value in (args.command, args.script, args.smoke))
    if selected != 1:
        _print_lines(
            stdout,
            ("CHASEOS // INVALID CLI USAGE", "Choose one of --command, --script, or --smoke."),
        )
        return EXIT_USAGE

    runner = HeadlessCommandRunner(
        sequence=sequence or StartupSequence(data_dir=base_path),
        allow_desktop_changes=args.allow_desktop_changes,
    )
    if args.command:
        run = runner.run_command(args.command)
        _print_command_run(stdout, run, include_header=False)
        return run.exit_code
    if args.script:
        runs = runner.run_script(Path(args.script))
        _print_script_runs(stdout, runs)
        return _aggregate_exit_code(runs)
    if args.smoke == "wallpapers":
        runs = runner.run_commands(WALLPAPER_SMOKE_COMMANDS)
        _print_script_runs(stdout, runs)
        _write_wallpaper_smoke_reports(runs, base_path=base_path)
        return _aggregate_exit_code(runs)
    if args.smoke == "startup":
        runs = runner.run_commands(STARTUP_SMOKE_INPUTS)
        _print_script_runs(stdout, runs)
        _write_startup_smoke_reports(
            runs,
            sequence=runner.sequence,
            base_path=base_path or runner.sequence.data_dir,
        )
        return _aggregate_exit_code(runs)
    if args.smoke == "release":
        runs = runner.run_commands(RELEASE_SMOKE_COMMANDS)
        _print_script_runs(stdout, runs)
        _write_release_smoke_reports(runs, base_path=base_path)
        return _aggregate_exit_code(runs)

    _print_lines(
        stdout,
        ("CHASEOS // INVALID CLI USAGE", "Supported smoke targets: wallpapers, startup, release."),
    )
    return EXIT_USAGE


class HeadlessCommandRunner:
    """Run routed ChaseOS commands without opening the GUI."""

    def __init__(
        self,
        sequence: StartupSequence | None = None,
        allow_desktop_changes: bool = False,
    ) -> None:
        self.sequence = sequence or StartupSequence()
        self.allow_desktop_changes = allow_desktop_changes

    def run_script(self, script_path: Path) -> tuple[HeadlessCommandRun, ...]:
        commands = []
        for line in script_path.read_text(encoding="utf-8").splitlines():
            command = line.strip()
            if not command or command.startswith("#"):
                continue
            commands.append(command)
        return self.run_commands(commands)

    def run_commands(self, commands: Iterable[str]) -> tuple[HeadlessCommandRun, ...]:
        return tuple(self.run_command(command) for command in commands)

    def run_command(self, command: str) -> HeadlessCommandRun:
        normalized = " ".join(command.strip().split()).lower()
        if self._is_blocked(normalized):
            return HeadlessCommandRun(
                command=command,
                output=(
                    "CHASEOS // COMMAND BLOCKED",
                    "",
                    "This command can change desktop wallpaper state.",
                    "Headless mode blocks it unless --allow-desktop-changes is provided.",
                    "",
                    "No changes applied.",
                ),
                exit_code=EXIT_BLOCKED,
                status="blocked",
            )

        result = route_command(command)
        output = self._execute(command, result)
        exit_code = _exit_code_for_output(output, result)
        return HeadlessCommandRun(
            command=command,
            output=output,
            exit_code=exit_code,
            status="passed" if exit_code == EXIT_SUCCESS else "failed",
        )

    def _is_blocked(self, normalized_command: str) -> bool:
        return (
            not self.allow_desktop_changes
            and normalized_command in MUTATING_COMMANDS
        )

    def _execute(self, command: str, result: CommandResult) -> tuple[str, ...]:
        if result.is_noop:
            return ()
        if result.command == "/help":
            return _render_lines(result.lines)
        if result.action == "clear":
            return ("clear command ignored in headless mode.",)
        if result.action == "exit":
            return _render_lines(result.lines)
        response = self.sequence.handle_input(command, result)
        return _render_lines(response.lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chaseos", add_help=True)
    parser.add_argument("--command", "-c")
    parser.add_argument("--script")
    parser.add_argument("--smoke", choices=("wallpapers", "startup", "release"))
    parser.add_argument("--allow-desktop-changes", action="store_true")
    return parser


def _exit_code_for_output(output: tuple[str, ...], result: CommandResult) -> int:
    text = "\n".join(output)
    failure_markers = (
        "PREFLIGHT FAILED",
        "DOCTOR FAILED",
        "PREPARE WALLPAPERS FAILED",
        "APPLY REFUSED",
        "wallpaper apply failed:",
        "wallpaper reset failed:",
        "unknown command.",
    )
    if not result.recognized or any(marker in text for marker in failure_markers):
        return EXIT_FAILURE
    return EXIT_SUCCESS


def _aggregate_exit_code(runs: tuple[HeadlessCommandRun, ...]) -> int:
    if any(run.exit_code == EXIT_BLOCKED for run in runs):
        return EXIT_BLOCKED
    if any(run.exit_code != EXIT_SUCCESS for run in runs):
        return EXIT_FAILURE
    return EXIT_SUCCESS


def _render_lines(lines: Iterable[TerminalLine]) -> tuple[str, ...]:
    return tuple(line.text for line in lines)


def _print_lines(stdout: TextIO, lines: tuple[str, ...]) -> None:
    for line in lines:
        print(line, file=stdout)


def _print_command_run(
    stdout: TextIO,
    run: HeadlessCommandRun,
    include_header: bool = True,
) -> None:
    if include_header:
        print(f"$ {run.command}", file=stdout)
    _print_lines(stdout, run.output)


def _print_script_runs(stdout: TextIO, runs: tuple[HeadlessCommandRun, ...]) -> None:
    for index, run in enumerate(runs):
        if index:
            print("", file=stdout)
        print(f"CHASEOS // COMMAND: {run.command}", file=stdout)
        _print_lines(stdout, run.output)


def _write_wallpaper_smoke_reports(
    runs: tuple[HeadlessCommandRun, ...],
    base_path: Path | str | None = None,
) -> None:
    started_at = datetime.now(UTC)
    completed_at = datetime.now(UTC)
    exit_code = _aggregate_exit_code(runs)
    aggregate_status = (
        "blocked"
        if exit_code == EXIT_BLOCKED
        else "passed"
        if exit_code == EXIT_SUCCESS
        else "failed"
    )
    text_path = get_last_wallpaper_smoke_text_path(base_path)
    json_path = get_last_wallpaper_smoke_json_path(base_path)
    text_path.parent.mkdir(parents=True, exist_ok=True)

    text_lines = [
        "CHASEOS // WALLPAPER SMOKE",
        f"aggregate_status: {aggregate_status}",
        f"exit_code: {exit_code}",
        "",
    ]
    for run in runs:
        text_lines.extend((f"$ {run.command}", f"status: {run.status}", *run.output, ""))
    text_path.write_text("\n".join(text_lines).rstrip() + "\n", encoding="utf-8")

    json_path.write_text(
        json.dumps(
            {
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
                "commands": [run.command for run in runs],
                "per_command": [
                    {
                        "command": run.command,
                        "status": run.status,
                        "exit_code": run.exit_code,
                        "output": list(run.output),
                    }
                    for run in runs
                ],
                "aggregate_status": aggregate_status,
                "exit_code": exit_code,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_startup_smoke_reports(
    runs: tuple[HeadlessCommandRun, ...],
    sequence: StartupSequence,
    base_path: Path | str | None = None,
) -> None:
    started_at = datetime.now(UTC)
    completed_at = datetime.now(UTC)
    exit_code = _aggregate_exit_code(runs)
    aggregate_status = (
        "blocked"
        if exit_code == EXIT_BLOCKED
        else "passed"
        if exit_code == EXIT_SUCCESS
        else "failed"
    )
    text_path = get_last_startup_smoke_text_path(base_path)
    json_path = get_last_startup_smoke_json_path(base_path)
    text_path.parent.mkdir(parents=True, exist_ok=True)
    sequence.write_daily_summary()
    session = sequence.daily_sessions.load()
    generated_assets = dict(session.generated_assets) if session else {}

    text_lines = [
        "CHASEOS // STARTUP SMOKE",
        "test_data: true",
        f"aggregate_status: {aggregate_status}",
        f"exit_code: {exit_code}",
        "",
    ]
    for run in runs:
        text_lines.extend((f"$ {run.command}", f"status: {run.status}", *run.output, ""))
    text_path.write_text("\n".join(text_lines).rstrip() + "\n", encoding="utf-8")

    json_path.write_text(
        json.dumps(
            {
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
                "test_data": True,
                "commands_or_inputs": [run.command for run in runs],
                "per_step": [
                    {
                        "command_or_input": run.command,
                        "status": run.status,
                        "exit_code": run.exit_code,
                        "output": list(run.output),
                    }
                    for run in runs
                ],
                "aggregate_status": aggregate_status,
                "exit_code": exit_code,
                "generated_asset_paths": generated_assets,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_release_smoke_reports(
    runs: tuple[HeadlessCommandRun, ...],
    base_path: Path | str | None = None,
) -> None:
    started_at = datetime.now(UTC)
    completed_at = datetime.now(UTC)
    exit_code = _aggregate_exit_code(runs)
    aggregate_status = (
        "blocked"
        if exit_code == EXIT_BLOCKED
        else "passed"
        if exit_code == EXIT_SUCCESS
        else "failed"
    )
    text_path = get_last_release_smoke_text_path(base_path)
    json_path = get_last_release_smoke_json_path(base_path)
    text_path.parent.mkdir(parents=True, exist_ok=True)

    text_lines = [
        "CHASEOS // RELEASE SMOKE",
        f"aggregate_status: {aggregate_status}",
        f"exit_code: {exit_code}",
        "no wallpaper changes applied: yes",
        "no startup changes applied: yes",
        "",
    ]
    for run in runs:
        text_lines.extend((f"$ {run.command}", f"status: {run.status}", *run.output, ""))
    text_path.write_text("\n".join(text_lines).rstrip() + "\n", encoding="utf-8")

    json_path.write_text(
        json.dumps(
            {
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
                "commands": [run.command for run in runs],
                "per_command": [
                    {
                        "command": run.command,
                        "status": run.status,
                        "exit_code": run.exit_code,
                        "output": list(run.output),
                    }
                    for run in runs
                ],
                "aggregate_status": aggregate_status,
                "exit_code": exit_code,
                "no_wallpaper_changes_applied": True,
                "no_startup_changes_applied": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
