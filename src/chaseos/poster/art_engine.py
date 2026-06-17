"""Display 1 generated art planning and rendering engine."""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path

from chaseos.models.poster import Display1ArtMetadata, Display1ArtPlan, PublicPosterRenderResult
from chaseos.models.theme import ThemeFamily, ThemePlan
from chaseos.poster.art_renderer import DISPLAY1_ART_SIZE, Display1ArtRenderer
from chaseos.poster.poster_archive import POSTER_IMAGE_NAME, POSTER_METADATA_NAME, PosterArchive
from chaseos.poster.poster_safety import public_safe_principle, validate_public_text
from chaseos.storage.paths import get_posters_dir


class Display1ArtEngine:
    """Coordinate text-free Display 1 art plans, rendering, and metadata."""

    def __init__(self, base_path: Path | str | None = None) -> None:
        self.base_path = Path(base_path) if base_path is not None else None
        self.renderer = Display1ArtRenderer()
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
    ) -> Display1ArtPlan:
        del innovation_exercise, run_date, output_directory
        changes = list(change_requests or [])
        safe_takeaway = public_safe_principle(private_innovation_takeaway)
        if not validate_public_text(safe_takeaway, raw_check_in=raw_check_in):
            raise ValueError("Display 1 art seed source failed safety validation.")
        seed = _stable_seed(safe_takeaway, regenerate_count)
        family = self._family(theme_plan, changes, regenerate_count)
        motif = self._motif(family, changes)
        intensity = theme_plan.cyberpunk_intensity if theme_plan else 0.64
        show_figure = True
        show_geometry = True
        show_scanlines = True
        if self._has_change(changes, "more cyberpunk", "more geometry"):
            intensity = min(1.0, max(0.7, intensity + 0.18))
            show_geometry = True
        if self._has_change(changes, "less geometry", "calmer skyline", "calmer"):
            intensity = max(0.18, intensity - 0.2)
            show_geometry = not self._has_change(changes, "less geometry")
        if self._has_change(changes, "darker"):
            intensity = max(0.3, intensity - 0.08)
        if self._has_change(changes, "brighter"):
            intensity = min(1.0, intensity + 0.1)
        if self._has_change(changes, "no figure"):
            show_figure = False
        return Display1ArtPlan(
            family=family,
            motif=motif,
            seed=seed,
            public_safe_takeaway=safe_takeaway,
            show_figure=show_figure,
            show_geometry=show_geometry,
            show_scanlines=show_scanlines,
            cyberpunk_intensity=round(intensity, 2),
            change_requests=changes,
            regenerate_count=regenerate_count,
        )

    def render(
        self,
        plan: Display1ArtPlan,
        innovation_exercise: str,
        private_innovation_takeaway: str,
        theme_plan: ThemePlan | None,
        run_date: date | None = None,
        output_directory: Path | str | None = None,
        approved: bool = True,
        force_regenerate: bool = False,
    ) -> PublicPosterRenderResult:
        del innovation_exercise, private_innovation_takeaway
        run_date = run_date or datetime.now(UTC).date()
        poster_dir = self._poster_dir(run_date, output_directory)
        image_path = poster_dir / POSTER_IMAGE_NAME
        metadata_path = poster_dir / POSTER_METADATA_NAME
        if image_path.exists() and metadata_path.exists() and not force_regenerate:
            return PublicPosterRenderResult(
                image_path=image_path,
                metadata_path=metadata_path,
                width=DISPLAY1_ART_SIZE[0],
                height=DISPLAY1_ART_SIZE[1],
            )
        result = self.renderer.render(plan, image_path, metadata_path, theme_plan=theme_plan)
        metadata = Display1ArtMetadata(
            date=run_date,
            generated_at=datetime.now(UTC),
            seed=plan.seed,
            family=plan.family.value,
            motif=plan.motif,
            image_path=str(image_path),
            width=result.width,
            height=result.height,
            approved=approved,
            change_requests=plan.change_requests,
            regenerate_count=plan.regenerate_count,
            cyberpunk_intensity=plan.cyberpunk_intensity,
            show_figure=plan.show_figure,
            show_geometry=plan.show_geometry,
            show_scanlines=plan.show_scanlines,
        )
        self.archive.save_metadata(metadata, metadata_path)
        return result

    def describe_plan(self, plan: Display1ArtPlan) -> str:
        return "\n".join(
            (
                "DISPLAY 1 ART PLAN",
                f"display ......... {plan.display}",
                f"size ............ {plan.width}x{plan.height}",
                f"family .......... {plan.family.value}",
                f"motif ........... {plan.motif}",
                f"seed ............ {plan.seed}",
                f"intensity ....... {round(plan.cyberpunk_intensity * 100)}%",
                f"figure .......... {'yes' if plan.show_figure else 'no'}",
                f"geometry ........ {'yes' if plan.show_geometry else 'no'}",
                "readable text ... no",
                "source .......... innovation takeaway seed only",
                f"safe ............ {'yes' if plan.safe else 'no'}",
            )
        )

    def _poster_dir(self, run_date: date, output_directory: Path | str | None = None) -> Path:
        if output_directory is not None:
            return get_posters_dir(run_date, output_directory)
        return get_posters_dir(run_date, self.base_path)

    def _family(
        self,
        theme_plan: ThemePlan | None,
        changes: list[str],
        regenerate_count: int,
    ) -> ThemeFamily:
        if self._has_change(changes, "ff7", "mako"):
            return ThemeFamily.MAKO_REACTOR
        if self._has_change(changes, "lofi"):
            return ThemeFamily.LOFI_DUSK
        if theme_plan and theme_plan.family in {
            ThemeFamily.DUSK_SKYLINE,
            ThemeFamily.MAKO_REACTOR,
            ThemeFamily.LOFI_DUSK,
        }:
            return theme_plan.family
        options = (ThemeFamily.DUSK_SKYLINE, ThemeFamily.MAKO_REACTOR, ThemeFamily.LOFI_DUSK)
        return options[regenerate_count % len(options)]

    def _motif(self, family: ThemeFamily, changes: list[str]) -> str:
        if family == ThemeFamily.MAKO_REACTOR:
            return "mako_reactor"
        if family == ThemeFamily.LOFI_DUSK:
            return "lofi_dusk"
        if self._has_change(changes, "calmer skyline"):
            return "calmer_skyline"
        return "dusk_skyline"

    def _has_change(self, change_requests: list[str], *needles: str) -> bool:
        text = " ".join(change_requests).lower()
        return any(needle in text for needle in needles)


def _stable_seed(public_safe_takeaway: str, regenerate_count: int) -> int:
    payload = f"{public_safe_takeaway}|{regenerate_count}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big", signed=False)
