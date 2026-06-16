"""Command parsing for the ChaseOS terminal shell.

This module intentionally has no PySide6 dependency so the command loop can be tested
without starting the GUI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Speaker = Literal["chaseos", "system", "user"]
CommandAction = Literal["noop", "text", "respond", "clear", "exit"]


@dataclass(frozen=True)
class TerminalLine:
    """A formatted terminal line emitted by the shell."""

    speaker: Speaker
    text: str

    def render(self) -> str:
        return f"{self.speaker}> {self.text}"


@dataclass(frozen=True)
class CommandResult:
    """Parsed command result for the GUI shell to apply."""

    action: CommandAction
    command: str | None = None
    argument: str | None = None
    lines: tuple[TerminalLine, ...] = ()
    recognized: bool = True
    change_request: str | None = None

    @property
    def is_noop(self) -> bool:
        return self.action == "noop"


KNOWN_COMMANDS = (
    "/help",
    "/start",
    "/clear",
    "/exit",
    "/reset",
    "/theme",
    "/poster",
    "/approve",
    "/regenerate",
    "/change",
    "/skip",
    "/status",
    "/monitors",
    "/monitor",
    "/detect",
    "/assign",
    "/auto",
    "/save",
    "/wallpapers",
    "/generate",
    "/photos",
    "/index",
    "/photo",
)


HELP_LINES = (
    TerminalLine("chaseos", "available commands:"),
    TerminalLine("chaseos", "/start - begin the 15-minute text ritual"),
    TerminalLine("chaseos", "/theme - print the current placeholder theme plan"),
    TerminalLine("chaseos", "/poster - print the current placeholder poster plan"),
    TerminalLine("chaseos", "/approve - approve the current ritual step"),
    TerminalLine("chaseos", "/change <text> - request a theme or poster adjustment"),
    TerminalLine("chaseos", "/regenerate - regenerate the active placeholder plan"),
    TerminalLine("chaseos", "/wallpapers - print generated private wallpaper paths"),
    TerminalLine("chaseos", "/generate wallpapers - generate private wallpapers if a theme exists"),
    TerminalLine("chaseos", "/photos - print local photo index status"),
    TerminalLine("chaseos", "/index photos - index the private Lightroom export folder"),
    TerminalLine("chaseos", "/photo source - print the configured local photo source"),
    TerminalLine("chaseos", "/monitors - detect monitors and print ChaseOS roles"),
    TerminalLine("chaseos", "/detect monitors - force fresh monitor detection"),
    TerminalLine("chaseos", "/monitor roles - print saved monitor role mapping"),
    TerminalLine("chaseos", "/assign display 1 public - assign a display to a role"),
    TerminalLine("chaseos", "/auto assign monitors - auto-map the ChaseOS monitor layout"),
    TerminalLine("chaseos", "/save monitors, /reset monitors"),
    TerminalLine("chaseos", "/status, /skip, /reset, /clear, /exit"),
)


MONITOR_LINES = (
    TerminalLine("chaseos", "display 1 -> Public Signal Monitor"),
    TerminalLine("chaseos", "display 4 -> Left Atmosphere Monitor"),
    TerminalLine("chaseos", "display 2 -> Center Command Monitor"),
    TerminalLine("chaseos", "display 3 -> Right Inspiration Monitor"),
)


class CommandRouter:
    """Parse terminal input into shell actions and response lines."""

    def route(self, raw_input: str) -> CommandResult:
        text = raw_input.strip()
        if not text:
            return CommandResult(action="noop", command=None)

        if not text.startswith("/"):
            return CommandResult(action="text", argument=text)

        command, _, argument = text.partition(" ")
        command = command.lower()
        argument = argument.strip()

        if command == "/help":
            return CommandResult(action="respond", command=command, lines=HELP_LINES)
        if command == "/start":
            return CommandResult(
                action="respond",
                command=command,
                lines=(TerminalLine("chaseos", "start sequence command recognized."),),
            )
        if command == "/clear":
            return CommandResult(action="clear", command=command)
        if command == "/exit":
            return CommandResult(
                action="exit",
                command=command,
                lines=(TerminalLine("system", "exiting ChaseOS."),),
            )
        if command == "/reset" and argument == "monitors":
            return CommandResult(
                action="respond",
                command="/reset monitors",
                argument=argument,
                lines=(TerminalLine("chaseos", "reset monitors command recognized."),),
            )
        if command == "/reset":
            return CommandResult(
                action="respond",
                command=command,
                lines=(TerminalLine("chaseos", "reset desktop placeholder ready."),),
            )
        if command == "/theme":
            return CommandResult(
                action="respond",
                command=command,
                lines=(TerminalLine("chaseos", "theme-plan placeholder ready."),),
            )
        if command == "/poster":
            return CommandResult(
                action="respond",
                command=command,
                lines=(TerminalLine("chaseos", "public-poster placeholder ready."),),
            )
        if command == "/approve":
            return CommandResult(
                action="respond",
                command=command,
                lines=(TerminalLine("chaseos", "approval placeholder recorded."),),
            )
        if command == "/regenerate":
            return CommandResult(
                action="respond",
                command=command,
                lines=(TerminalLine("chaseos", "regeneration placeholder queued."),),
            )
        if command == "/change":
            if not argument:
                return CommandResult(
                    action="respond",
                    command=command,
                    argument=None,
                    lines=(TerminalLine("chaseos", "change request missing. try /change calmer."),),
                    change_request=None,
                )
            return CommandResult(
                action="respond",
                command=command,
                argument=argument,
                lines=(TerminalLine("chaseos", f"change request captured: {argument}"),),
                change_request=argument,
            )
        if command == "/skip":
            return CommandResult(
                action="respond",
                command=command,
                lines=(TerminalLine("chaseos", "skip placeholder acknowledged."),),
            )
        if command == "/status":
            return CommandResult(
                action="respond",
                command=command,
                lines=(
                    TerminalLine(
                        "chaseos",
                        "shell status: idle. ritual engine not implemented yet.",
                    ),
                ),
            )
        if command == "/monitors":
            return CommandResult(
                action="respond",
                command=command,
                lines=(TerminalLine("chaseos", "monitor detection command recognized."),),
            )
        if command == "/monitor" and argument == "roles":
            return CommandResult(
                action="respond",
                command="/monitor roles",
                argument=argument,
                lines=(TerminalLine("chaseos", "monitor roles command recognized."),),
            )
        if command == "/detect" and argument == "monitors":
            return CommandResult(
                action="respond",
                command="/detect monitors",
                argument=argument,
                lines=(TerminalLine("chaseos", "detect monitors command recognized."),),
            )
        if command == "/assign":
            return CommandResult(
                action="respond",
                command=command,
                argument=argument,
                lines=(TerminalLine("chaseos", "monitor assignment command recognized."),),
            )
        if command == "/auto" and argument == "assign monitors":
            return CommandResult(
                action="respond",
                command="/auto assign monitors",
                argument=argument,
                lines=(TerminalLine("chaseos", "auto assign monitors command recognized."),),
            )
        if command == "/save" and argument == "monitors":
            return CommandResult(
                action="respond",
                command="/save monitors",
                argument=argument,
                lines=(TerminalLine("chaseos", "save monitors command recognized."),),
            )
        if command == "/wallpapers":
            return CommandResult(
                action="respond",
                command=command,
                lines=(TerminalLine("chaseos", "wallpaper paths command recognized."),),
            )
        if command == "/photos":
            return CommandResult(
                action="respond",
                command=command,
                lines=(TerminalLine("chaseos", "photo status command recognized."),),
            )
        if command == "/index" and argument == "photos":
            return CommandResult(
                action="respond",
                command="/index photos",
                argument=argument,
                lines=(TerminalLine("chaseos", "photo indexing command recognized."),),
            )
        if command == "/photo" and argument == "source":
            return CommandResult(
                action="respond",
                command="/photo source",
                argument=argument,
                lines=(TerminalLine("chaseos", "photo source command recognized."),),
            )
        if command == "/generate" and argument == "wallpapers":
            return CommandResult(
                action="respond",
                command="/generate wallpapers",
                argument=argument,
                lines=(TerminalLine("chaseos", "generate wallpapers command recognized."),),
            )

        return CommandResult(
            action="respond",
            command=command if command.startswith("/") else None,
            argument=argument or None,
            lines=(
                TerminalLine(
                    "chaseos",
                    "unknown command. type /help unless you enjoy guessing.",
                ),
            ),
            recognized=False,
        )


def route_command(raw_input: str) -> CommandResult:
    """Convenience wrapper for callers that do not need a router instance."""

    return CommandRouter().route(raw_input)
