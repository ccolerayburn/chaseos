"""Public innovation poster planning and rendering engine."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from chaseos.models.poster import (
    PublicPosterMetadata,
    PublicPosterPlan,
    PublicPosterRenderResult,
    PublicPosterStyle,
)
from chaseos.models.theme import ThemeFamily, ThemePlan
from chaseos.poster.poster_archive import POSTER_IMAGE_NAME, POSTER_METADATA_NAME, PosterArchive
from chaseos.poster.poster_renderer import PUBLIC_POSTER_SIZE, PublicPosterRenderer
from chaseos.poster.poster_safety import (
    public_safe_principle,
    redact_sensitive_public_text,
    validate_public_text,
)
from chaseos.poster.quote_engine import QuoteEngine
from chaseos.storage.paths import get_posters_dir


class PublicPosterEngine:
    """Coordinate public-safe poster plans, rendering, and metadata."""

    def __init__(self, base_path: Path | str | None = None) -> None:
        self.base_path = Path(base_path) if base_path is not None else None
        self.quote_engine = QuoteEngine()
        self.renderer = PublicPosterRenderer()
        self.archive = PosterArchive()

    def build_plan(
        self,
        innovation_exercise: str,
        private_innovation_takeaway: str,
        theme_plan: ThemePlan | None,
        run_date: date | None = None,
        output_directory: Path | str | None = None,
        change_requests: list[str] | tuple[str, ...] | None = None,
        regenerate_count: int = 0,
        raw_check_in: str | None = None,
    ) -> PublicPosterPlan:
        del innovation_exercise, run_date, output_directory
        changes = list(change_requests or [])
        safe_takeaway = public_safe_principle(private_innovation_takeaway)
        quote = self.quote_engine.generate_quote(
            safe_takeaway,
            change_requests=changes,
            regenerate_count=regenerate_count,
        )
        quote = redact_sensitive_public_text(quote)
        style = self._style_from_theme(theme_plan, regenerate_count)
        subtitle = None if self._has_change(changes, "no subtitle") else "Daily Innovation Signal"
        visual_density = "minimal"
        intensity = theme_plan.cyberpunk_intensity if theme_plan else 0.45
        if self._has_change(changes, "more minimal"):
            visual_density = "minimal"
            intensity = min(intensity, 0.35)
        if self._has_change(changes, "more cyberpunk"):
            visual_density = "medium"
            intensity = min(0.85, max(intensity + 0.18, 0.58))

        plan = PublicPosterPlan(
            style_family=style,
            quote=quote,
            subtitle=subtitle,
            public_safe_takeaway=safe_takeaway,
            visual_density=visual_density,
            cyberpunk_intensity=round(intensity, 2),
            change_requests=changes,
            regenerate_count=regenerate_count,
        )
        public_text = self.describe_plan(plan)
        if not validate_public_text(public_text, raw_check_in=raw_check_in):
            raise ValueError("Public poster plan failed safety validation.")
        return plan

    def render(
        self,
        plan: PublicPosterPlan,
        innovation_exercise: str,
        private_innovation_takeaway: str,
        theme_plan: ThemePlan | None,
        run_date: date | None = None,
        output_directory: Path | str | None = None,
        approved: bool = True,
        force_regenerate: bool = False,
    ) -> PublicPosterRenderResult:
        run_date = run_date or datetime.now(UTC).date()
        poster_dir = self._poster_dir(run_date, output_directory)
        image_path = poster_dir / POSTER_IMAGE_NAME
        metadata_path = poster_dir / POSTER_METADATA_NAME

        if image_path.exists() and metadata_path.exists() and not force_regenerate:
            return PublicPosterRenderResult(
                image_path=image_path,
                metadata_path=metadata_path,
                width=PUBLIC_POSTER_SIZE[0],
                height=PUBLIC_POSTER_SIZE[1],
            )

        result = self.renderer.render(
            plan=plan,
            image_path=image_path,
            metadata_path=metadata_path,
            theme_plan=theme_plan,
        )
        metadata = PublicPosterMetadata(
            date=run_date,
            generated_at=datetime.now(UTC),
            innovation_exercise=innovation_exercise,
            private_takeaway=private_innovation_takeaway,
            public_safe_takeaway=plan.public_safe_takeaway,
            quote=plan.quote,
            subtitle=plan.subtitle,
            style_family=plan.style_family.value,
            image_path=str(image_path),
            width=result.width,
            height=result.height,
            approved=approved,
            change_requests=plan.change_requests,
            regenerate_count=plan.regenerate_count,
        )
        self.archive.save_metadata(metadata, metadata_path)
        return result

    def describe_plan(self, plan: PublicPosterPlan) -> str:
        subtitle = plan.subtitle if plan.subtitle else "none"
        return "\n".join(
            (
                "PUBLIC POSTER PLAN",
                f"display ......... {plan.display}",
                f"size ............ {plan.width}x{plan.height}",
                f"style ........... {plan.style_family.value}",
                f'quote ........... "{plan.quote}"',
                f"subtitle ........ {subtitle}",
                "source .......... innovation takeaway only",
                f"safe ............ {'yes' if plan.safe else 'no'}",
            )
        )

    def _poster_dir(self, run_date: date, output_directory: Path | str | None = None) -> Path:
        if output_directory is not None:
            return get_posters_dir(run_date, output_directory)
        return get_posters_dir(run_date, self.base_path)

    def _style_from_theme(
        self,
        theme_plan: ThemePlan | None,
        regenerate_count: int,
    ) -> PublicPosterStyle:
        if theme_plan is None:
            return PublicPosterStyle.OBSIDIAN_SIGNAL
        mapping = {
            ThemeFamily.OBSIDIAN_TERMINAL: (
                PublicPosterStyle.OBSIDIAN_SIGNAL,
                PublicPosterStyle.NEON_BLUEPRINT,
            ),
            ThemeFamily.CHROME_MONOLITH: (PublicPosterStyle.CHROME_MONOLITH,),
            ThemeFamily.VIOLET_CIRCUIT: (PublicPosterStyle.VIOLET_CIRCUIT,),
            ThemeFamily.REDLINE_PROTOCOL: (PublicPosterStyle.REDLINE_PROTOCOL,),
            ThemeFamily.ARCTIC_INTERFACE: (PublicPosterStyle.ARCTIC_INTERFACE,),
            ThemeFamily.SYNTH_SANCTUARY: (
                PublicPosterStyle.SYNTHETIC_SUNRISE,
                PublicPosterStyle.OBSIDIAN_SIGNAL,
            ),
            ThemeFamily.SYNTHETIC_SUNRISE: (PublicPosterStyle.SYNTHETIC_SUNRISE,),
            ThemeFamily.NEON_NOIR: (PublicPosterStyle.NEON_BLUEPRINT,),
            ThemeFamily.DUSK_SKYLINE: (PublicPosterStyle.SYNTHETIC_SUNRISE,),
            ThemeFamily.MAKO_REACTOR: (PublicPosterStyle.NEON_BLUEPRINT,),
            ThemeFamily.LOFI_DUSK: (PublicPosterStyle.SYNTHETIC_SUNRISE,),
        }
        options = mapping.get(theme_plan.family, (PublicPosterStyle.OBSIDIAN_SIGNAL,))
        return options[regenerate_count % len(options)]

    def _has_change(self, change_requests: list[str], *needles: str) -> bool:
        text = " ".join(change_requests).lower()
        return any(needle in text for needle in needles)
