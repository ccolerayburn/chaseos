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
    "/version",
    "/doctor",
    "/start",
    "/daily",
    "/export",
    "/startup",
    "/install",
    "/uninstall",
    "/release",
    "/resume",
    "/clear",
    "/exit",
    "/reset",
    "/apply",
    "/wallpaper",
    "/assets",
    "/prepare",
    "/verify",
    "/theme",
    "/poster",
    "/approve",
    "/regenerate",
    "/change",
    "/takeaway",
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


HELP_TOPICS: dict[str, tuple[str, ...]] = {
    "": (
        "CHASEOS // HELP",
        "",
        "Startup ritual",
        "  /start - begin the daily text ritual",
        "  /daily status - show today's session without raw check-in text",
        "  /daily summary - write/show a redacted operational summary",
        "  /resume - resume today's ritual",
        "",
        "Theme and approval",
        "  /approve, /skip - advance the active ritual step",
        "  /change <text> - request a theme or Display 1 art adjustment",
        "  /regenerate - regenerate the active plan",
        "  /takeaway <text> - capture the innovation insight during improv",
        "  /theme, /poster, /wallpapers - show current plans or paths",
        "  art changes: more cyberpunk, lofi, mako, darker, brighter, more geometry",
        "",
        "Daily assets",
        "  /assets status - check generated asset readiness",
        "  /prepare wallpapers --takeaway-file <path> - generate assets only",
        "  /generate wallpapers - generate private wallpapers after a theme exists",
        "",
        "Wallpaper verification and apply",
        "  /wallpaper status, /wallpaper diagnostics, /verify wallpapers",
        "  /apply wallpapers --dry-run - preview only",
        "  /apply wallpapers --confirm - explicit live apply command",
        "  /reset wallpapers - restore rollback state",
        "",
        "Monitor mapping",
        "  /monitors, /detect monitors, /monitor roles",
        "  /assign display 1 public, /auto assign monitors, /save monitors",
        "",
        "Photos",
        "  /photos, /index photos, /photo source",
        "",
        "Readiness and diagnostics",
        "  /doctor, /status, /version, /release info",
        "  /export support --dry-run, /export support --redacted",
        "  /startup status - inspect per-user Startup shortcut",
        "  /install shortcut - create a Start Menu shortcut for taskbar pinning",
        "",
        "Headless usage",
        '  python -m chaseos --command "/daily status"',
        "  python -m chaseos --smoke startup",
        "",
        "Safety notes",
        "  Optional improv can use the API only when explicitly enabled.",
        "  Display 1 generated art has no readable text; no general Lightroom/local photos.",
        "  Raw check-in text is not persisted by default.",
        "  Help, status, diagnostics, smoke, export, verify, and dry-run do not apply.",
    ),
    "startup": (
        "CHASEOS // HELP STARTUP",
        "/start begins the daily ritual.",
        "/daily status shows today's session without raw check-in text.",
        "/daily summary writes a redacted operational summary.",
        "/resume resumes today's ritual where practical.",
        "/approve advances the active step; it is not a hidden wallpaper apply.",
    ),
    "wallpapers": (
        "CHASEOS // HELP WALLPAPERS",
        "/prepare wallpapers generates assets only.",
        "/verify wallpapers runs strict preflight and changes nothing.",
        "/apply wallpapers --dry-run previews per-monitor changes only.",
        "/apply wallpapers --confirm is the explicit live apply command.",
        "Headless live apply also requires --allow-desktop-changes.",
        "/reset wallpapers restores rollback state and changes desktop state.",
    ),
    "monitors": (
        "CHASEOS // HELP MONITORS",
        "/monitors detects monitors and prints ChaseOS roles.",
        "/detect monitors forces fresh detection.",
        "/monitor roles prints saved role mapping.",
        "/assign display 1 public assigns a display to a role.",
        "/auto assign monitors maps the known ChaseOS layout.",
        "/save monitors persists the current mapping.",
    ),
    "photos": (
        "CHASEOS // HELP PHOTOS",
        "/photos prints local photo source and index status.",
        "/index photos indexes the private Lightroom export folder locally.",
        "/photo source prints the configured source.",
        "Display 1 generated art has no readable text and no general local photos.",
    ),
    "headless": (
        "CHASEOS // HELP HEADLESS",
        'python -m chaseos --command "/help wallpapers"',
        'python -m chaseos --command "/daily summary"',
        'python -m chaseos --command "/export support --dry-run"',
        "python -m chaseos --smoke startup",
        "Live apply requires --allow-desktop-changes and explicit confirm.",
    ),
    "safety": (
        "CHASEOS // HELP SAFETY",
        "Raw check-in text is not persisted by default.",
        "Daily status and summary use practical non-clinical signals only.",
        "Display 1 generated art has no readable text and no general local photos.",
        "/prepare, /verify, /apply --dry-run, smoke, help, status, and export do not apply.",
        "/apply wallpapers --confirm is the explicit live apply command.",
        "Optional improv uses the API only when enabled; no admin, registry, or Explorer work.",
    ),
}


def help_lines(topic: str = "") -> tuple[TerminalLine, ...]:
    normalized = topic.strip().lower()
    lines = HELP_TOPICS.get(normalized)
    if lines is None:
        lines = (
            "CHASEOS // HELP",
            f"unknown help topic: {topic}",
            "topics: startup, wallpapers, monitors, photos, headless, safety",
        )
    return tuple(TerminalLine("chaseos", line) for line in lines)


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
            return CommandResult(
                action="respond",
                command=command,
                argument=argument,
                lines=help_lines(argument),
            )
        if command == "/version":
            return CommandResult(
                action="respond",
                command=command,
                lines=(TerminalLine("chaseos", "version command recognized."),),
            )
        if command == "/doctor":
            return CommandResult(
                action="respond",
                command=command,
                lines=(TerminalLine("chaseos", "doctor command recognized."),),
            )
        if command == "/start":
            return CommandResult(
                action="respond",
                command=command,
                lines=(TerminalLine("chaseos", "start sequence command recognized."),),
            )
        if command == "/daily" and argument in {"status", "summary"}:
            return CommandResult(
                action="respond",
                command=f"/daily {argument}",
                argument=argument,
                lines=(TerminalLine("chaseos", f"daily {argument} command recognized."),),
            )
        if command == "/startup" and argument in {"status", "enable", "disable"}:
            return CommandResult(
                action="respond",
                command=f"/startup {argument}",
                argument=argument,
                lines=(TerminalLine("chaseos", f"startup {argument} command recognized."),),
            )
        if command == "/install" and argument == "shortcut":
            return CommandResult(
                action="respond",
                command="/install shortcut",
                argument=argument,
                lines=(TerminalLine("chaseos", "install shortcut command recognized."),),
            )
        if command == "/uninstall" and argument == "shortcut":
            return CommandResult(
                action="respond",
                command="/uninstall shortcut",
                argument=argument,
                lines=(TerminalLine("chaseos", "uninstall shortcut command recognized."),),
            )
        if command == "/release" and argument == "info":
            return CommandResult(
                action="respond",
                command="/release info",
                argument=argument,
                lines=(TerminalLine("chaseos", "release info command recognized."),),
            )
        if command == "/resume":
            return CommandResult(
                action="respond",
                command=command,
                lines=(TerminalLine("chaseos", "resume command recognized."),),
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
        if command == "/reset" and argument == "wallpapers":
            return CommandResult(
                action="respond",
                command="/reset wallpapers",
                argument=argument,
                lines=(TerminalLine("chaseos", "reset wallpapers command recognized."),),
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
                lines=(TerminalLine("chaseos", "display 1 art placeholder ready."),),
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
        if command == "/takeaway":
            if not argument:
                return CommandResult(
                    action="respond",
                    command=command,
                    argument=None,
                    lines=(
                        TerminalLine(
                            "chaseos",
                            "takeaway missing. try /takeaway automate the repeat question.",
                        ),
                    ),
                )
            return CommandResult(
                action="respond",
                command=command,
                argument=argument,
                lines=(TerminalLine("chaseos", "innovation takeaway captured."),),
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
        if command == "/wallpaper" and argument in {"status", "diagnostics"}:
            return CommandResult(
                action="respond",
                command=f"/wallpaper {argument}",
                argument=argument,
                lines=(TerminalLine("chaseos", f"wallpaper {argument} command recognized."),),
            )
        if command == "/assets" and argument == "status":
            return CommandResult(
                action="respond",
                command="/assets status",
                argument=argument,
                lines=(TerminalLine("chaseos", "assets status command recognized."),),
            )
        if command == "/prepare" and argument.startswith("wallpapers"):
            return CommandResult(
                action="respond",
                command="/prepare wallpapers",
                argument=argument.removeprefix("wallpapers").strip(),
                lines=(TerminalLine("chaseos", "prepare wallpapers command recognized."),),
            )
        if command == "/verify" and argument == "wallpapers":
            return CommandResult(
                action="respond",
                command="/verify wallpapers",
                argument=argument,
                lines=(TerminalLine("chaseos", "verify wallpapers command recognized."),),
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
        if command == "/export" and argument.startswith("support"):
            return CommandResult(
                action="respond",
                command="/export support",
                argument=argument.removeprefix("support").strip(),
                lines=(TerminalLine("chaseos", "support export command recognized."),),
            )
        if command == "/generate" and argument == "wallpapers":
            return CommandResult(
                action="respond",
                command="/generate wallpapers",
                argument=argument,
                lines=(TerminalLine("chaseos", "generate wallpapers command recognized."),),
            )
        if command == "/apply" and argument in {
            "wallpapers",
            "wallpapers --dry-run",
            "wallpapers --confirm",
        }:
            return CommandResult(
                action="respond",
                command="/apply wallpapers",
                argument=argument.removeprefix("wallpapers").strip(),
                lines=(TerminalLine("chaseos", "apply wallpapers command recognized."),),
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
