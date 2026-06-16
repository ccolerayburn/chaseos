"""Text-only 15-minute ChaseOS startup ritual state machine."""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

from chaseos import __version__
from chaseos.app.command_router import CommandResult, TerminalLine, route_command
from chaseos.app.readiness import ReadinessService
from chaseos.interpretation.checkin_interpreter import LocalCheckInInterpreter
from chaseos.models.assets import WallpaperManifest
from chaseos.models.monitor import (
    ROLE_DISPLAY_NAMES,
    MonitorLayout,
    MonitorRole,
    resolve_monitor_role,
)
from chaseos.models.poster import PublicPosterPlan, PublicPosterRenderResult
from chaseos.models.signals import PracticalSignals, StartupMode
from chaseos.models.theme import ThemePlan
from chaseos.poster.public_poster_engine import PublicPosterEngine
from chaseos.ritual.prompts import (
    APPLYING_LINES,
    CHECK_IN_PROMPT,
    INNOVATION_WARMUP_LINES,
    MINDFULNESS_LINES,
    VERSE_LINES,
    WORK_RAMP_LINES,
)
from chaseos.ritual.stages import RitualStage
from chaseos.ritual.timer import RITUAL_TARGET_MINUTES, RitualTimer
from chaseos.storage.daily_session_store import DailySessionRecord, DailySessionStore
from chaseos.storage.paths import get_generated_dir
from chaseos.storage.settings_store import MonitorMappingStore
from chaseos.theming.theme_generator import ThemeGenerator
from chaseos.wallpaper.applier import WallpaperApplier, WallpaperApplyError
from chaseos.wallpaper.diagnostics import WallpaperDiagnosticsService
from chaseos.wallpaper.photo_indexer import PhotoLibraryIndexer
from chaseos.wallpaper.photo_source import PhotoSourceConfig
from chaseos.wallpaper.plan import WallpaperApplyPlanner, WallpaperPlanError
from chaseos.wallpaper.wallpaper_composer import WallpaperComposer
from chaseos.wallpaper.wallpaper_manifest import WALLPAPER_MANIFEST_NAME, WallpaperManifestStore
from chaseos.windows import display_detection
from chaseos.windows.monitor_roles import (
    REQUIRED_PRIVATE_ROLES,
    assign_monitor_role,
    auto_assign_known_layout,
    summarize_monitor_layout,
)

STARTUP_SEQUENCE_STAGES = tuple(stage.value for stage in RitualStage)


@dataclass
class RitualSession:
    """In-memory session data for the current startup ritual."""

    started_at: datetime | None = None
    completed_at: datetime | None = None
    current_stage: RitualStage = RitualStage.IDLE
    raw_check_in: str | None = None
    placeholder_signals: dict[str, str] = field(default_factory=dict)
    signals: PracticalSignals | None = None
    interpretation_summary: tuple[str, ...] = ()
    startup_mode: str = "Structured Start"
    theme_change_requests: list[str] = field(default_factory=list)
    theme_approved: bool = False
    innovation_takeaway: str | None = None
    innovation_exercise: str = "10% Less Dumb"
    poster_change_requests: list[str] = field(default_factory=list)
    poster_approved: bool = False
    theme_regenerate_count: int = 0
    poster_regenerate_count: int = 0
    theme_plan: ThemePlan | None = None
    public_safe_takeaway: str | None = None
    public_quote: str | None = None
    poster_plan: PublicPosterPlan | None = None
    poster_render_result: PublicPosterRenderResult | None = None
    private_wallpaper_manifest: WallpaperManifest | None = None
    private_wallpaper_paths: dict[str, Path] = field(default_factory=dict)
    private_wallpapers_generated: bool = False
    wallpaper_regenerate_count: int = 0
    current_theme_plan: str = ""
    current_poster_plan: str = ""


@dataclass(frozen=True)
class SequenceResponse:
    """Terminal-friendly response from the ritual engine."""

    lines: tuple[TerminalLine, ...] = ()


def _chaseos_lines(lines: tuple[str, ...]) -> tuple[TerminalLine, ...]:
    return tuple(TerminalLine("chaseos", line) for line in lines)


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


class StartupSequence:
    """Owns the current ritual stage, timer, and in-memory session data."""

    def __init__(
        self,
        target_minutes: int = RITUAL_TARGET_MINUTES,
        data_dir: Path | str | None = None,
        photo_config: PhotoSourceConfig | None = None,
        wallpaper_applier: WallpaperApplier | None = None,
    ) -> None:
        self.data_dir = Path(data_dir) if data_dir is not None else None
        self.timer = RitualTimer(target_minutes=target_minutes)
        self.session = RitualSession()
        self.interpreter = LocalCheckInInterpreter()
        self.theme_generator = ThemeGenerator()
        self.poster_engine = PublicPosterEngine(base_path=self.data_dir)
        self.photo_config = photo_config or PhotoSourceConfig()
        self.photo_indexer = PhotoLibraryIndexer(config=self.photo_config, base_path=self.data_dir)
        self.monitor_mapping_store = MonitorMappingStore(base_path=self.data_dir)
        self.monitor_layout: MonitorLayout | None = None
        self.wallpaper_composer = WallpaperComposer(
            base_path=self.data_dir,
            photo_config=self.photo_config,
        )
        self.wallpaper_planner = WallpaperApplyPlanner(
            base_path=self.data_dir,
            photo_config=self.photo_config,
        )
        self.wallpaper_applier = wallpaper_applier or WallpaperApplier(base_path=self.data_dir)
        self.wallpaper_diagnostics = WallpaperDiagnosticsService(
            planner=self.wallpaper_planner,
            client=self.wallpaper_applier.client,
            base_path=self.data_dir,
        )
        self.readiness = ReadinessService(
            base_path=self.data_dir,
            photo_config=self.photo_config,
        )
        self.daily_sessions = DailySessionStore(base_path=self.data_dir)

    @property
    def current_stage(self) -> RitualStage:
        return self.session.current_stage

    @property
    def is_active(self) -> bool:
        return self.current_stage not in {
            RitualStage.IDLE,
            RitualStage.COMPLETE,
            RitualStage.CANCELLED,
            RitualStage.RESET,
        }

    def handle_input(
        self,
        raw_input: str,
        command_result: CommandResult | None = None,
    ) -> SequenceResponse:
        result = command_result or route_command(raw_input)
        if result.is_noop:
            return SequenceResponse()

        if result.command == "/start":
            return self.start()
        if result.command == "/daily status":
            return SequenceResponse(_chaseos_lines(self.daily_status_lines()))
        if result.command == "/resume":
            return self.resume_daily_session()
        if result.command == "/version":
            return SequenceResponse(self.version_lines())
        if result.command == "/doctor":
            return SequenceResponse(_chaseos_lines(self.readiness.doctor_lines()))
        if result.command == "/reset monitors":
            return self.handle_reset_monitors()
        if result.command == "/reset wallpapers":
            return self.handle_reset_wallpapers()
        if result.command == "/reset":
            return self.reset()
        if result.command == "/status":
            return SequenceResponse(self.status_lines())
        if result.command == "/monitors":
            return self.handle_monitors()
        if result.command == "/detect monitors":
            return self.handle_detect_monitors()
        if result.command == "/monitor roles":
            return SequenceResponse(self.monitor_role_lines())
        if result.command == "/assign":
            return self.handle_assign_monitor(result.argument or "")
        if result.command == "/auto assign monitors":
            return self.handle_auto_assign_monitors()
        if result.command == "/save monitors":
            return self.handle_save_monitors()
        if result.command == "/theme":
            return SequenceResponse(self.theme_lines_or_placeholder())
        if result.command == "/poster":
            return SequenceResponse(self.poster_lines_or_placeholder())
        if result.command == "/wallpapers":
            return SequenceResponse(self.wallpaper_lines_or_placeholder())
        if result.command == "/assets status":
            return SequenceResponse(_chaseos_lines(self.readiness.assets_status_lines()))
        if result.command == "/prepare wallpapers":
            return SequenceResponse(
                _chaseos_lines(self.readiness.prepare_wallpapers_lines(result.argument or ""))
            )
        if result.command == "/wallpaper status":
            return self.handle_wallpaper_status()
        if result.command == "/wallpaper diagnostics":
            return self.handle_wallpaper_diagnostics()
        if result.command == "/verify wallpapers":
            return self.handle_verify_wallpapers()
        if result.command == "/generate wallpapers":
            return self.handle_generate_wallpapers()
        if result.command == "/apply wallpapers":
            return self.handle_apply_wallpapers(result.argument or "")
        if result.command == "/photos":
            return SequenceResponse(self.photo_status_lines())
        if result.command == "/index photos":
            return self.handle_index_photos()
        if result.command == "/photo source":
            return SequenceResponse(self.photo_source_lines())
        if not result.recognized and result.command is not None:
            return SequenceResponse(
                (TerminalLine("chaseos", "unknown command. type /help unless you enjoy guessing."),)
            )

        if self.current_stage == RitualStage.IDLE:
            return SequenceResponse((TerminalLine("chaseos", "type /start to begin."),))
        if self.current_stage == RitualStage.COMPLETE:
            return SequenceResponse(
                (TerminalLine("chaseos", "sequence already complete. type /start to run again."),)
            )

        if self.current_stage == RitualStage.CHECK_IN and result.action == "text":
            return self.capture_check_in(result.argument or raw_input.strip())

        if self.current_stage == RitualStage.THEME_APPROVAL:
            return self.handle_theme_approval(result)

        if self.current_stage == RitualStage.MINDFULNESS:
            return self.handle_mindfulness(result)

        if self.current_stage == RitualStage.VERSE:
            return self.handle_verse(result)

        if self.current_stage == RitualStage.INNOVATION_TAKEAWAY and result.action == "text":
            return self.capture_innovation_takeaway(result.argument or raw_input.strip())

        if self.current_stage == RitualStage.POSTER_APPROVAL:
            return self.handle_poster_approval(result)

        if self.current_stage == RitualStage.WORK_RAMP:
            return self.handle_work_ramp(result)

        return SequenceResponse(
            (TerminalLine("chaseos", "that input is not available in this ritual stage."),)
        )

    def start(self) -> SequenceResponse:
        self.timer.start()
        started_at = self.timer.started_at or datetime.now(UTC)
        self.session = RitualSession(started_at=started_at, current_stage=RitualStage.CHECK_IN)
        self.save_daily_session()
        return SequenceResponse(
            _chaseos_lines(
                (
                    "start sequence initialized.",
                    f"target duration: {self.timer.target_minutes} minutes.",
                    CHECK_IN_PROMPT,
                )
            )
        )

    def reset(self) -> SequenceResponse:
        self.timer.reset()
        self.session = RitualSession(current_stage=RitualStage.IDLE)
        return SequenceResponse((TerminalLine("chaseos", "ritual reset. type /start to begin."),))

    def capture_check_in(self, check_in: str) -> SequenceResponse:
        self.session.raw_check_in = check_in
        self.session.current_stage = RitualStage.INTERPRETING
        interpretation = self.interpreter.interpret(check_in)
        self.session.signals = interpretation.signals
        self.session.placeholder_signals = interpretation.signals.model_dump(mode="json")
        self.session.startup_mode = interpretation.startup_mode.value
        self.session.interpretation_summary = interpretation.user_facing_summary

        lines = [
            "INTERPRETING",
            f"signals ......... {self.format_signals(interpretation.signals)}",
            f"startup mode .... {self.session.startup_mode}",
        ]
        lines.extend(f"summary ......... {line}" for line in interpretation.user_facing_summary)
        self.session.current_stage = RitualStage.THEME_PLAN
        self.session.current_theme_plan = self.build_theme_plan()
        lines.extend(self.session.current_theme_plan.splitlines())
        self.session.current_stage = RitualStage.THEME_APPROVAL
        self.save_daily_session()
        lines.extend(
            (
                "approve this setup, change something, or regenerate?",
                "commands: /approve, /change <request>, /regenerate, /skip",
            )
        )
        return SequenceResponse(_chaseos_lines(tuple(lines)))

    def handle_theme_approval(self, result: CommandResult) -> SequenceResponse:
        if result.command in {"/approve", "/skip"}:
            self.session.theme_approved = True
            self.session.current_stage = RitualStage.MINDFULNESS
            self.save_daily_session()
            return SequenceResponse(_chaseos_lines(MINDFULNESS_LINES))

        if result.command == "/change":
            if not result.change_request:
                return SequenceResponse(
                    (TerminalLine("chaseos", "change request missing. try /change calmer."),)
                )
            self.session.theme_change_requests.append(result.change_request)
            self.session.current_theme_plan = self.build_theme_plan()
            self.save_daily_session()
            lines = [
                "theme change request recorded.",
                *self.session.current_theme_plan.splitlines(),
            ]
            lines.extend(
                (
                    "approve this setup, change something, or regenerate?",
                    "commands: /approve, /change <request>, /regenerate, /skip",
                )
            )
            return SequenceResponse(_chaseos_lines(tuple(lines)))

        if result.command == "/regenerate":
            self.session.theme_regenerate_count += 1
            self.session.current_theme_plan = self.build_theme_plan()
            self.save_daily_session()
            lines = ["theme plan regenerated.", *self.session.current_theme_plan.splitlines()]
            lines.extend(
                (
                    "approve this setup, change something, or regenerate?",
                    "commands: /approve, /change <request>, /regenerate, /skip",
                )
            )
            return SequenceResponse(_chaseos_lines(tuple(lines)))

        return SequenceResponse(
            (TerminalLine("chaseos", "use /approve, /change <request>, /regenerate, or /skip."),)
        )

    def handle_mindfulness(self, result: CommandResult) -> SequenceResponse:
        if self._is_continue_signal(result):
            self.session.current_stage = RitualStage.VERSE
            self.save_daily_session()
            return SequenceResponse(_chaseos_lines(VERSE_LINES))
        return SequenceResponse(
            (TerminalLine("chaseos", "type done, /approve, or /skip to continue."),)
        )

    def handle_verse(self, result: CommandResult) -> SequenceResponse:
        if self._is_continue_signal(result):
            self.session.current_stage = RitualStage.INNOVATION
            lines = [*INNOVATION_WARMUP_LINES, "what is today's useful insight?"]
            self.session.current_stage = RitualStage.INNOVATION_TAKEAWAY
            self.save_daily_session()
            return SequenceResponse(_chaseos_lines(tuple(lines)))
        return SequenceResponse(
            (TerminalLine("chaseos", "type done, /approve, or /skip to continue."),)
        )

    def capture_innovation_takeaway(self, takeaway: str) -> SequenceResponse:
        self.session.innovation_takeaway = takeaway
        self.session.current_stage = RitualStage.POSTER_PLAN
        self.session.current_poster_plan = self.build_poster_plan()
        self.session.current_stage = RitualStage.POSTER_APPROVAL
        self.save_daily_session()
        lines = [*self.session.current_poster_plan.splitlines()]
        lines.extend(
            (
                "approve poster, change quote, or regenerate?",
                "commands: /approve, /change <request>, /regenerate, /poster, /skip",
            )
        )
        return SequenceResponse(_chaseos_lines(tuple(lines)))

    def handle_poster_approval(self, result: CommandResult) -> SequenceResponse:
        if result.command in {"/approve", "/skip"}:
            self.session.poster_approved = True
            render_result = self.render_current_poster()
            self.session.current_stage = RitualStage.WORK_RAMP
            self.save_daily_session()
            lines = [
                f"poster rendered: {render_result.image_path}",
                f"metadata saved: {render_result.metadata_path}",
                *WORK_RAMP_LINES,
            ]
            return SequenceResponse(_chaseos_lines(tuple(lines)))

        if result.command == "/change":
            if not result.change_request:
                return SequenceResponse(
                    (TerminalLine("chaseos", "poster change missing. try /change sharper quote."),)
                )
            self.session.poster_change_requests.append(result.change_request)
            self.session.current_poster_plan = self.build_poster_plan(revised=True)
            self.save_daily_session()
            lines = [
                "poster change request recorded.",
                *self.session.current_poster_plan.splitlines(),
            ]
            lines.extend(
                (
                    "approve poster, change quote, or regenerate?",
                    "commands: /approve, /change <request>, /regenerate, /poster, /skip",
                )
            )
            return SequenceResponse(_chaseos_lines(tuple(lines)))

        if result.command == "/regenerate":
            self.session.poster_regenerate_count += 1
            self.session.current_poster_plan = self.build_poster_plan()
            self.save_daily_session()
            lines = ["poster plan regenerated.", *self.session.current_poster_plan.splitlines()]
            lines.extend(
                (
                    "approve poster, change quote, or regenerate?",
                    "commands: /approve, /change <request>, /regenerate, /poster, /skip",
                )
            )
            return SequenceResponse(_chaseos_lines(tuple(lines)))

        return SequenceResponse(
            (TerminalLine("chaseos", "use /approve, /change <request>, /regenerate, or /skip."),)
        )

    def handle_work_ramp(self, result: CommandResult) -> SequenceResponse:
        if self._is_continue_signal(result):
            self.session.current_stage = RitualStage.APPLYING
            manifest, preflight_lines, dry_run_lines, preflight_status, dry_run_status = (
                self.generate_daily_assets_with_checks()
            )
            lines = [
                *APPLYING_LINES,
                "",
                "GENERATING DAILY ASSETS",
                "display 4 -> left atmosphere",
                "display 2 -> center command",
                "display 3 -> right inspiration",
                "",
                *self.wallpaper_output_lines(manifest),
                "",
                *self.readiness.assets_status_lines(),
                "",
                *preflight_lines,
                "",
                *dry_run_lines,
                "",
                "Daily assets are ready.",
                "No desktop wallpaper changes were applied.",
                "Run /apply wallpapers --confirm to apply them.",
                "start sequence complete.",
            ]
            self.session.current_stage = RitualStage.COMPLETE
            self.session.completed_at = datetime.now(UTC)
            self.timer.stop()
            self.save_daily_session(
                preflight_status=preflight_status,
                dry_run_status=dry_run_status,
            )
            return SequenceResponse(_chaseos_lines(tuple(lines)))
        return SequenceResponse(
            (TerminalLine("chaseos", "type done, /approve, or /skip to complete."),)
        )

    def build_theme_plan(self) -> str:
        signals = self.session.signals or PracticalSignals()
        result = self.theme_generator.generate(
            signals=signals,
            startup_mode=self.session.startup_mode or StartupMode.STRUCTURED,
            change_requests=self.session.theme_change_requests,
            regenerate_count=self.session.theme_regenerate_count,
        )
        self.session.theme_plan = result.plan
        return result.description_text

    def build_poster_plan(self, revised: bool = False) -> str:
        del revised
        plan = self.poster_engine.build_plan(
            innovation_exercise=self.session.innovation_exercise,
            private_innovation_takeaway=self.session.innovation_takeaway or "",
            theme_plan=self.session.theme_plan,
            change_requests=self.session.poster_change_requests,
            regenerate_count=self.session.poster_regenerate_count,
            raw_check_in=self.session.raw_check_in,
        )
        self.session.poster_plan = plan
        self.session.public_safe_takeaway = plan.public_safe_takeaway
        self.session.public_quote = plan.quote
        return self.poster_engine.describe_plan(plan)

    def render_current_poster(self) -> PublicPosterRenderResult:
        if self.session.poster_plan is None:
            self.session.current_poster_plan = self.build_poster_plan()
        assert self.session.poster_plan is not None
        render_result = self.poster_engine.render(
            plan=self.session.poster_plan,
            innovation_exercise=self.session.innovation_exercise,
            private_innovation_takeaway=self.session.innovation_takeaway or "",
            theme_plan=self.session.theme_plan,
            approved=self.session.poster_approved,
            force_regenerate=bool(
                self.session.poster_change_requests or self.session.poster_regenerate_count
            ),
        )
        self.session.poster_render_result = render_result
        return render_result

    def handle_generate_wallpapers(self) -> SequenceResponse:
        if self.session.theme_plan is None:
            return SequenceResponse(
                (
                    TerminalLine(
                        "chaseos",
                        "no theme plan yet. type /start and finish the check-in first.",
                    ),
                )
            )
        self.session.wallpaper_regenerate_count += 1
        manifest = self.generate_private_wallpapers()
        lines = [
            "GENERATING PRIVATE WALLPAPERS",
            "display 4 -> left atmosphere",
            "display 2 -> center command",
            "display 3 -> right inspiration",
            "",
            *self.wallpaper_output_lines(manifest),
            "wallpapers generated locally.",
            "no Windows wallpaper changes applied without /apply wallpapers --confirm.",
        ]
        return SequenceResponse(_chaseos_lines(tuple(lines)))

    def handle_apply_wallpapers(self, argument: str) -> SequenceResponse:
        confirm = argument == "--confirm"
        if argument not in {"", "--dry-run", "--confirm"}:
            return SequenceResponse(
                (
                    TerminalLine(
                        "chaseos",
                        "use /apply wallpapers --dry-run or /apply wallpapers --confirm.",
                    ),
                )
            )

        try:
            layout = self.detect_and_assign_monitors(use_saved=True)
            plan = self.wallpaper_planner.build_plan(layout)
            diagnostics = self.wallpaper_diagnostics.build(layout)
            lines = (
                self._apply_confirmed_after_preflight(plan, diagnostics)
                if confirm
                else self.wallpaper_applier.dry_run(plan, diagnostics=diagnostics)
            )
        except (WallpaperPlanError, WallpaperApplyError, OSError, ValueError) as exc:
            return SequenceResponse((TerminalLine("chaseos", f"wallpaper apply failed: {exc}"),))

        return SequenceResponse(_chaseos_lines(tuple(lines)))

    def _apply_confirmed_after_preflight(self, plan, diagnostics) -> tuple[str, ...]:
        issues = self.wallpaper_diagnostics.strict_issues(diagnostics)
        if issues:
            lines = ["CHASEOS // WALLPAPER APPLY REFUSED", ""]
            lines.extend(f"issue: {issue}" for issue in issues)
            lines.extend(("No changes applied.",))
            return tuple(lines)
        resolved_ids = {
            target.target.monitor_id: target.resolved_monitor_id
            for target in diagnostics.targets
            if target.resolved_monitor_id
        }
        return self.wallpaper_applier.apply_confirmed(plan, resolved_monitor_ids=resolved_ids)

    def handle_reset_wallpapers(self) -> SequenceResponse:
        try:
            lines = self.wallpaper_applier.reset()
        except (WallpaperApplyError, OSError, ValueError) as exc:
            return SequenceResponse((TerminalLine("chaseos", f"wallpaper reset failed: {exc}"),))
        return SequenceResponse(_chaseos_lines(tuple(lines)))

    def handle_wallpaper_status(self) -> SequenceResponse:
        layout = self.detect_and_assign_monitors(use_saved=True)
        return SequenceResponse(_chaseos_lines(self.wallpaper_diagnostics.status_lines(layout)))

    def handle_wallpaper_diagnostics(self) -> SequenceResponse:
        layout = self.detect_and_assign_monitors(use_saved=True)
        return SequenceResponse(
            _chaseos_lines(self.wallpaper_diagnostics.diagnostics_lines(layout))
        )

    def handle_verify_wallpapers(self) -> SequenceResponse:
        layout = self.detect_and_assign_monitors(use_saved=True)
        return SequenceResponse(_chaseos_lines(self.wallpaper_diagnostics.verify_lines(layout)))

    def handle_index_photos(self) -> SequenceResponse:
        if not self.photo_indexer.source_exists():
            return SequenceResponse(
                _chaseos_lines(
                    (
                        f"photo source: {self.photo_config.source_path}",
                        "photo source not found. generated wallpapers will be used.",
                        "public monitor photo usage remains disabled.",
                    )
                )
            )

        photo_index = self.photo_indexer.index()
        return SequenceResponse(
            _chaseos_lines(
                (
                    "indexing local photo source complete.",
                    f"indexed images: {photo_index.photo_count}",
                    "public monitor photo usage remains disabled.",
                )
            )
        )

    def handle_monitors(self) -> SequenceResponse:
        layout = self.detect_and_assign_monitors(use_saved=True)
        return self.monitor_layout_response(layout)

    def handle_detect_monitors(self) -> SequenceResponse:
        layout = self.detect_and_assign_monitors(use_saved=False)
        return self.monitor_layout_response(layout)

    def handle_auto_assign_monitors(self) -> SequenceResponse:
        layout = self.detect_and_assign_monitors(use_saved=False)
        self.monitor_mapping_store.save_layout(layout)
        lines = [
            "auto-assigned monitor roles.",
            f"mapping saved: {self.monitor_mapping_store.path}",
            "",
            *summarize_monitor_layout(layout, saved_mapping_exists=True),
        ]
        return self._monitor_lines(tuple(lines), layout)

    def handle_save_monitors(self) -> SequenceResponse:
        layout = self.monitor_layout or self.detect_and_assign_monitors(use_saved=True)
        if not layout.assignments:
            return SequenceResponse(
                (TerminalLine("chaseos", "no monitor assignments available to save."),)
            )
        self.monitor_mapping_store.save_layout(layout)
        return SequenceResponse(
            _chaseos_lines(
                (
                    "monitor role mapping saved.",
                    f"config path: {self.monitor_mapping_store.path}",
                    "use /apply wallpapers --dry-run to preview wallpaper application.",
                )
            )
        )

    def handle_reset_monitors(self) -> SequenceResponse:
        self.monitor_mapping_store.clear()
        self.monitor_layout = self.detect_and_assign_monitors(use_saved=False)
        return SequenceResponse(
            _chaseos_lines(
                (
                    "monitor role mapping reset.",
                    "saved monitor mapping cleared.",
                    "auto-detect/fallback behavior is active.",
                    "use /apply wallpapers --dry-run to preview wallpaper application.",
                )
            )
        )

    def handle_assign_monitor(self, argument: str) -> SequenceResponse:
        try:
            display_id, role = self.parse_assignment_argument(argument)
            layout = self.monitor_layout or self.detect_and_assign_monitors(use_saved=True)
            resolved_role = resolve_monitor_role(role)
            assign_monitor_role(layout, display_id, role)
            self.monitor_layout = layout
            self.monitor_mapping_store.save_layout(layout)
            assignment = layout.assignments[resolved_role]
            role_label = ROLE_DISPLAY_NAMES[assignment.role]
        except ValueError as exc:
            return SequenceResponse((TerminalLine("chaseos", f"monitor assignment failed: {exc}"),))

        display_label = assignment.display_label or assignment.stable_id
        return SequenceResponse(
            _chaseos_lines(
                (
                    f"assigned {display_label} -> {role_label}.",
                    f"mapping saved: {self.monitor_mapping_store.path}",
                    "use /apply wallpapers --dry-run to preview wallpaper application.",
                )
            )
        )

    def generate_private_wallpapers(self) -> WallpaperManifest:
        if self.session.theme_plan is None:
            raise RuntimeError("Theme plan is required before generating wallpapers.")
        public_poster_path = (
            self.session.poster_render_result.image_path
            if self.session.poster_render_result is not None
            else None
        )
        manifest = self.wallpaper_composer.generate(
            theme_plan=self.session.theme_plan,
            public_poster_path=public_poster_path,
            regenerate_count=self.session.wallpaper_regenerate_count,
        )
        self.session.private_wallpaper_manifest = manifest
        self.session.private_wallpapers_generated = True
        self.session.private_wallpaper_paths = {
            key: wallpaper.image_path
            for key, wallpaper in manifest.wallpapers.items()
            if key in {"display_4", "display_2", "display_3"}
        }
        return manifest

    def generate_daily_assets_with_checks(
        self,
    ) -> tuple[WallpaperManifest, tuple[str, ...], tuple[str, ...], str, str]:
        manifest = self.generate_private_wallpapers()
        try:
            layout = self.detect_and_assign_monitors(use_saved=True)
            diagnostics = self.wallpaper_diagnostics.build(layout)
            preflight_lines = self.wallpaper_diagnostics.verify_lines(layout)
            plan = self.wallpaper_planner.build_plan(layout)
            dry_run_lines = self.wallpaper_applier.dry_run(plan, diagnostics=diagnostics)
            preflight_status = "passed" if "PREFLIGHT PASSED" in preflight_lines[0] else "failed"
            dry_run_status = "passed"
        except (WallpaperPlanError, WallpaperApplyError, OSError, ValueError) as exc:
            preflight_status = "failed"
            dry_run_status = "failed"
            preflight_lines = (
                "CHASEOS // WALLPAPER PREFLIGHT FAILED",
                "",
                f"issue: {exc}",
                "No changes applied.",
            )
            dry_run_lines = (
                "CHASEOS // WALLPAPER APPLY DRY RUN FAILED",
                "",
                f"issue: {exc}",
                "No changes applied.",
            )
            self.save_daily_session(last_error=str(exc))
        return (
            manifest,
            tuple(preflight_lines),
            tuple(dry_run_lines),
            preflight_status,
            dry_run_status,
        )

    def wallpaper_output_lines(self, manifest: WallpaperManifest) -> list[str]:
        public_poster = (
            str(manifest.public_poster_path)
            if manifest.public_poster_path is not None
            else "not generated"
        )
        return [
            "WALLPAPER OUTPUTS",
            f"display 1 -> public poster: {public_poster}",
            f"display 4 -> left atmosphere: {manifest.wallpapers['display_4'].image_path}",
            f"display 2 -> center command: {manifest.wallpapers['display_2'].image_path}",
            f"display 3 -> right inspiration: {manifest.wallpapers['display_3'].image_path}",
            f"manifest . {manifest.manifest_path}",
        ]

    def theme_lines_or_placeholder(self) -> tuple[TerminalLine, ...]:
        if not self.session.current_theme_plan:
            return (TerminalLine("chaseos", "no theme plan yet. type /start to begin."),)
        return _chaseos_lines(tuple(self.session.current_theme_plan.splitlines()))

    def poster_lines_or_placeholder(self) -> tuple[TerminalLine, ...]:
        if not self.session.current_poster_plan:
            return (
                TerminalLine("chaseos", "no poster plan yet. complete the innovation step first."),
            )
        return _chaseos_lines(tuple(self.session.current_poster_plan.splitlines()))

    def wallpaper_lines_or_placeholder(self) -> tuple[TerminalLine, ...]:
        if self.session.private_wallpaper_manifest is None:
            return (
                TerminalLine(
                    "chaseos",
                    (
                        "no private wallpapers generated yet. "
                        "use /generate wallpapers after a theme exists."
                    ),
                ),
            )
        return _chaseos_lines(
            tuple(self.wallpaper_output_lines(self.session.private_wallpaper_manifest))
        )

    def daily_status_lines(self) -> tuple[str, ...]:
        record = self.daily_sessions.load()
        session_path = self.daily_sessions.path()
        if record is None:
            manifest = self.today_manifest()
            if manifest is None:
                return (
                    "CHASEOS // DAILY STATUS",
                    f"session path: {session_path}",
                    "No daily startup session found for today.",
                    "Run /start to begin.",
                    "No wallpaper changes applied.",
                )
            return (
                "CHASEOS // DAILY STATUS",
                f"session path: {session_path}",
                "No active ritual session found, but today's generated assets exist.",
                "Run /assets status or /apply wallpapers --dry-run to inspect them.",
                f"wallpaper manifest: {manifest.manifest_path}",
                "No wallpaper changes applied.",
            )

        lines = [
            "CHASEOS // DAILY STATUS",
            f"session path: {session_path}",
            f"current stage: {record.current_stage}",
            f"startup mode: {record.startup_mode}",
            f"theme approved: {'yes' if record.theme_approved else 'no'}",
            f"innovation takeaway exists: {'yes' if record.innovation_takeaway else 'no'}",
            f"poster/assets generated: {'yes' if record.generated_assets else 'no'}",
            f"wallpaper preflight passed: {_yes_no(record.preflight_status == 'passed')}",
            f"wallpaper dry-run passed: {_yes_no(record.dry_run_status == 'passed')}",
            f"live apply occurred today: {_yes_no(self.live_apply_occurred_today())}",
            f"applied status: {record.applied_status or 'not applied by ritual'}",
        ]
        if record.wallpaper_manifest_path:
            lines.append(f"wallpaper manifest: {record.wallpaper_manifest_path}")
        for label, path in record.generated_assets.items():
            lines.append(f"{label}: {path}")
        if record.last_error:
            lines.append(f"last error: {record.last_error}")
        lines.append("No wallpaper changes applied.")
        return tuple(lines)

    def resume_daily_session(self) -> SequenceResponse:
        record = self.daily_sessions.load()
        if record is None:
            return SequenceResponse(
                _chaseos_lines(
                    (
                        "No daily startup session found for today.",
                        "Run /start to begin.",
                        "No wallpaper changes applied.",
                    )
                )
            )

        try:
            self.session.current_stage = RitualStage(record.current_stage)
        except ValueError:
            self.session.current_stage = RitualStage.IDLE
        self.session.startup_mode = record.startup_mode
        self.session.placeholder_signals = dict(record.practical_signals)
        if record.practical_signals:
            self.session.signals = PracticalSignals.model_validate(record.practical_signals)
        self.session.theme_approved = record.theme_approved
        self.session.innovation_takeaway = record.innovation_takeaway
        self.session.poster_approved = record.poster_approved
        if self.session.signals is not None:
            self.session.current_theme_plan = self.build_theme_plan()
        self.session.private_wallpapers_generated = bool(record.generated_assets)
        if record.wallpaper_manifest_path:
            manifest = WallpaperManifestStore().load(Path(record.wallpaper_manifest_path))
            self.session.private_wallpaper_manifest = manifest

        lines = [
            "resumed today's daily session.",
            f"current stage: {self.session.current_stage.value}",
            f"session path: {self.daily_sessions.path()}",
        ]
        if record.generated_assets:
            lines.extend(
                (
                    f"preflight status: {record.preflight_status or 'unknown'}",
                    f"dry-run status: {record.dry_run_status or 'unknown'}",
                    "Run /apply wallpapers --confirm to apply them.",
                )
            )
        lines.append("No wallpaper changes applied.")
        return SequenceResponse(_chaseos_lines(tuple(lines)))

    def save_daily_session(
        self,
        *,
        preflight_status: str | None = None,
        dry_run_status: str | None = None,
        last_error: str | None = None,
    ) -> None:
        started_at = self.session.started_at or datetime.now(UTC)
        existing = self.daily_sessions.load()
        record = DailySessionRecord(
            date=date.today(),
            started_at=existing.started_at if existing else started_at,
            updated_at=datetime.now(UTC),
            current_stage=self.session.current_stage.value,
            startup_mode=self.session.startup_mode,
            practical_signals=self._practical_signals_for_record(),
            theme_plan_summary=self._theme_plan_summary(),
            theme_approved=self.session.theme_approved,
            innovation_takeaway=self.session.innovation_takeaway,
            poster_approved=self.session.poster_approved,
            generated_assets=self._generated_asset_paths(),
            wallpaper_manifest_path=self._manifest_path_for_record(),
            preflight_status=preflight_status
            if preflight_status is not None
            else existing.preflight_status
            if existing
            else None,
            dry_run_status=dry_run_status
            if dry_run_status is not None
            else existing.dry_run_status
            if existing
            else None,
            applied_status="not_applied_by_ritual",
            last_error=(
                last_error
                if last_error is not None
                else existing.last_error
                if existing
                else None
            ),
        )
        self.daily_sessions.save(record)

    def _practical_signals_for_record(self) -> dict[str, object]:
        if self.session.signals is not None:
            return self.session.signals.model_dump(mode="json")
        return dict(self.session.placeholder_signals)

    def _theme_plan_summary(self) -> str | None:
        if self.session.theme_plan is None:
            return None
        return (
            f"{self.session.theme_plan.family.value}; "
            f"{self.session.theme_plan.palette_label}; "
            f"{self.session.theme_plan.visual_density.value}"
        )

    def _generated_asset_paths(self) -> dict[str, str]:
        manifest = self.session.private_wallpaper_manifest
        assets: dict[str, str] = {}
        if manifest is None:
            if self.session.poster_render_result is not None:
                assets["display_1_public_poster"] = str(
                    self.session.poster_render_result.image_path
                )
            return assets
        if manifest.public_poster_path is not None:
            assets["display_1_public_poster"] = str(manifest.public_poster_path)
        for key in ("display_4", "display_2", "display_3"):
            wallpaper = manifest.wallpapers.get(key)
            if wallpaper is not None:
                assets[key] = str(wallpaper.image_path)
        return assets

    def _manifest_path_for_record(self) -> str | None:
        if self.session.private_wallpaper_manifest is None:
            return None
        return str(self.session.private_wallpaper_manifest.manifest_path)

    def today_manifest(self) -> WallpaperManifest | None:
        path = get_generated_dir(date.today(), self.data_dir) / WALLPAPER_MANIFEST_NAME
        return WallpaperManifestStore().load(path)

    def live_apply_occurred_today(self) -> bool:
        path = self.wallpaper_applier.last_apply_manifest_path
        if not path.exists():
            return False
        try:
            import json

            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        return payload.get("generated_date") == date.today().isoformat()

    def monitor_role_lines(self) -> tuple[TerminalLine, ...]:
        config = self.monitor_mapping_store.load()
        if config is None or not config.assignments:
            return _chaseos_lines(
                (
                    "MONITOR ROLES",
                    "saved mapping ... no",
                    "use /auto assign monitors or /assign display 1 public.",
                    "wallpaper application is not enabled in phase 8.",
                )
            )

        lines = ["MONITOR ROLES", "saved mapping ... yes"]
        for role in (
            MonitorRole.PUBLIC_SIGNAL,
            MonitorRole.LEFT_ATMOSPHERE,
            MonitorRole.CENTER_COMMAND,
            MonitorRole.RIGHT_INSPIRATION,
        ):
            assignment = config.assignments.get(role)
            target = (
                assignment.display_label or assignment.stable_id
                if assignment
                else "unassigned"
            )
            lines.append(f"{ROLE_DISPLAY_NAMES[role]} .... {target}")
        lines.append("wallpaper application is not enabled in phase 8.")
        return _chaseos_lines(tuple(lines))

    def detect_and_assign_monitors(self, use_saved: bool) -> MonitorLayout:
        layout = display_detection.detect_monitor_layout(use_fallback=True)
        saved = self.monitor_mapping_store.load() if use_saved else None
        layout = auto_assign_known_layout(layout, saved_config=saved)
        self.monitor_layout = layout
        return layout

    def monitor_layout_response(self, layout: MonitorLayout) -> SequenceResponse:
        return self._monitor_lines(
            summarize_monitor_layout(
                layout,
                saved_mapping_exists=self.monitor_mapping_store.exists(),
            ),
            layout,
        )

    def _monitor_lines(self, lines: tuple[str, ...], layout: MonitorLayout) -> SequenceResponse:
        terminal_lines = [TerminalLine("chaseos", line) for line in lines]
        detection_unavailable = any(
            "real monitor detection unavailable" in warning for warning in layout.warnings
        )
        if layout.source == "fallback" or detection_unavailable:
            terminal_lines.append(
                TerminalLine(
                    "system",
                    "real monitor detection unavailable. using known ChaseOS fallback layout.",
                )
            )
        for warning in layout.warnings:
            if "real monitor detection unavailable" in warning:
                continue
            terminal_lines.append(TerminalLine("system", warning))
        return SequenceResponse(tuple(terminal_lines))

    def parse_assignment_argument(self, argument: str) -> tuple[str, str]:
        parts = argument.strip().split()
        if len(parts) < 2:
            raise ValueError("use /assign display 1 public or /assign 1 public")

        role = parts[-1]
        display_id = " ".join(parts[:-1])
        if display_id.lower() == "display":
            raise ValueError("display number missing")
        return display_id, role

    def photo_source_lines(self) -> tuple[TerminalLine, ...]:
        return _chaseos_lines((f"photo source: {self.photo_config.source_path}",))

    def photo_status_lines(self) -> tuple[TerminalLine, ...]:
        source_exists = self.photo_indexer.source_exists()
        index_exists = self.photo_indexer.index_path.exists()
        lines = [
            "PHOTO LIBRARY",
            f"source path: {self.photo_config.source_path}",
            f"source exists: {'yes' if source_exists else 'no'}",
            f"index exists: {'yes' if index_exists else 'no'}",
            "public use: disabled",
        ]
        if index_exists:
            photo_index = self.photo_indexer.load()
            if photo_index is not None:
                lines.extend(
                    (
                        f"indexed images: {photo_index.photo_count}",
                        f"last indexed: {photo_index.indexed_at.isoformat()}",
                    )
                )
        if not source_exists:
            lines.append("photo source not found. generated wallpapers will be used.")
        return _chaseos_lines(tuple(lines))

    def status_lines(self) -> tuple[TerminalLine, ...]:
        active = "yes" if self.is_active else "no"
        monitor_config = self.monitor_mapping_store.load()
        monitor_assignments = (
            self.monitor_layout.assignments
            if self.monitor_layout is not None
            else monitor_config.assignments
            if monitor_config is not None
            else {}
        )
        monitor_source = (
            self.monitor_layout.source
            if self.monitor_layout is not None
            else "saved"
            if monitor_config is not None
            else "unknown"
        )
        public_role_assigned = MonitorRole.PUBLIC_SIGNAL in monitor_assignments
        private_roles_assigned = all(role in monitor_assignments for role in REQUIRED_PRIVATE_ROLES)
        return _chaseos_lines(
            (
                f"current stage: {self.current_stage.value}",
                f"elapsed time: {self.timer.elapsed_label}",
                f"remaining target time: {self.timer.remaining_label}",
                f"ritual active: {active}",
                f"public poster generated: {'yes' if self.session.poster_render_result else 'no'}",
                (
                    "private wallpapers generated: "
                    f"{'yes' if self.session.private_wallpapers_generated else 'no'}"
                ),
                (
                    "photo index available: "
                    f"{'yes' if self.photo_indexer.index_path.exists() else 'no'}"
                ),
                (
                    "monitor mapping exists: "
                    f"{'yes' if self.monitor_mapping_store.exists() else 'no'}"
                ),
                (
                    "wallpaper apply manifest exists: "
                    f"{'yes' if self.wallpaper_applier.last_apply_manifest_path.exists() else 'no'}"
                ),
                f"monitor mapping source: {monitor_source}",
                f"public signal role assigned: {'yes' if public_role_assigned else 'no'}",
                f"private roles assigned: {'yes' if private_roles_assigned else 'no'}",
            )
        )

    def version_lines(self) -> tuple[TerminalLine, ...]:
        return _chaseos_lines(
            (
                "CHASEOS // VERSION",
                "app: ChaseOS",
                f"version: {__version__}",
                "phase: 11 headless command runner and wallpaper smoke workflow",
                f"python: {sys.version.split()[0]}",
                f"platform: {platform.platform()}",
            )
        )

    def _is_continue_signal(self, result: CommandResult) -> bool:
        if result.command in {"/approve", "/skip"}:
            return True
        if result.action == "text":
            return bool(result.argument and result.argument.strip())
        return False

    def format_signals(self, signals: PracticalSignals) -> str:
        body_context = ", ".join(signals.body_context) if signals.body_context else "none"
        return (
            f"energy={signals.energy.value}; "
            f"clarity={signals.clarity.value}; "
            f"pressure={signals.pressure.value}; "
            f"mood_weight={signals.mood_weight.value}; "
            f"focus_friction={signals.focus_friction.value}; "
            f"body_context={body_context}; "
            f"social_battery={signals.social_battery.value}; "
            f"readiness={signals.readiness.value}"
        )
