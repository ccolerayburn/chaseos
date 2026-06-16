"""Coordinate generation of private monitor wallpapers."""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path

from chaseos.models.assets import PhotoIndex, WallpaperManifest
from chaseos.models.theme import ThemePlan
from chaseos.storage.paths import get_generated_dir
from chaseos.storage.settings_store import MonitorMappingStore
from chaseos.wallpaper.photo_indexer import PhotoLibraryIndexer
from chaseos.wallpaper.photo_selector import PhotoSelector
from chaseos.wallpaper.photo_source import PhotoSourceConfig
from chaseos.wallpaper.wallpaper_manifest import WALLPAPER_MANIFEST_NAME, WallpaperManifestStore
from chaseos.wallpaper.wallpaper_renderer import (
    DEFAULT_WALLPAPER_SIZE,
    PUBLIC_SIGNAL_SIZE,
    WallpaperRenderer,
    WallpaperRenderSpec,
)
from chaseos.windows.display_detection import get_fallback_monitor_layout
from chaseos.windows.monitor_roles import role_mapping_for_manifest

DEFAULT_TARGET_SIZES = {
    1: PUBLIC_SIGNAL_SIZE,
    4: DEFAULT_WALLPAPER_SIZE,
    2: DEFAULT_WALLPAPER_SIZE,
    3: DEFAULT_WALLPAPER_SIZE,
}

WALLPAPER_TARGETS = {
    1: {
        "role": "public_signal",
        "style": "generated_minimal",
        "filename": "display_1_public_signal.png",
    },
    4: {
        "role": "left_atmosphere",
        "style": "atmosphere_gradient",
        "filename": "display_4_left_atmosphere.png",
    },
    2: {
        "role": "center_command",
        "style": "command_grid",
        "filename": "display_2_center_command.png",
    },
    3: {
        "role": "right_inspiration",
        "style": "inspiration_geometry",
        "filename": "display_3_right_inspiration.png",
    },
}


class WallpaperComposer:
    """Generate ChaseOS wallpapers and their manifest."""

    def __init__(
        self,
        base_path: Path | str | None = None,
        photo_config: PhotoSourceConfig | None = None,
    ) -> None:
        self.base_path = Path(base_path) if base_path is not None else None
        self.renderer = WallpaperRenderer()
        self.manifest_store = WallpaperManifestStore()
        self.photo_config = photo_config or PhotoSourceConfig()
        self.photo_indexer = PhotoLibraryIndexer(config=self.photo_config, base_path=self.base_path)
        self.photo_selector = PhotoSelector(config=self.photo_config)
        self.monitor_mapping_store = MonitorMappingStore(base_path=self.base_path)

    def generate(
        self,
        theme_plan: ThemePlan,
        run_date: date | None = None,
        output_directory: Path | str | None = None,
        output_folder: Path | str | None = None,
        target_sizes: dict[int, tuple[int, int]] | None = None,
        public_poster_path: Path | str | None = None,
        photo_index: PhotoIndex | None = None,
        use_photo_index: bool = True,
        regenerate_count: int = 0,
    ) -> WallpaperManifest:
        run_date = run_date or datetime.now(UTC).date()
        target_sizes = target_sizes or DEFAULT_TARGET_SIZES
        output_dir = Path(output_folder) if output_folder is not None else self._output_dir(
            run_date,
            output_directory,
        )
        wallpapers = {}
        resolved_photo_index, index_error = self._resolve_photo_index(photo_index, use_photo_index)
        photo_selections = self.photo_selector.select_for_private_displays(
            resolved_photo_index,
            theme_plan,
            today=run_date,
            index_error=index_error,
        )

        for display_id, target in WALLPAPER_TARGETS.items():
            if display_id == 1 and public_poster_path is not None:
                continue

            default_size = PUBLIC_SIGNAL_SIZE if display_id == 1 else DEFAULT_WALLPAPER_SIZE
            width, height = target_sizes.get(display_id, default_size)
            role = target["role"]
            selection = photo_selections.get(f"display_{display_id}")
            spec = WallpaperRenderSpec(
                display_id=display_id,
                role=role,
                style=target["style"],
                width=width,
                height=height,
                output_path=output_dir / target["filename"],
                seed=self.daily_seed(run_date, theme_plan, role, regenerate_count),
                photo_path=selection.selected_photo_path if selection is not None else None,
                photo_mode=selection.mode if selection is not None else "generated",
                fallback_reason=selection.fallback_reason if selection is not None else None,
            )
            wallpapers[f"display_{display_id}"] = self.renderer.render(spec, theme_plan)

        poster_path = (
            Path(public_poster_path)
            if public_poster_path is not None
            else wallpapers["display_1"].image_path
        )
        fallback_reasons = {
            key: selection.fallback_reason
            for key, selection in photo_selections.items()
            if selection.fallback_reason
        }
        monitor_mapping_source, role_mapping = self._monitor_mapping_reference()
        manifest = WallpaperManifest(
            date=run_date,
            generated_at=datetime.now(UTC),
            theme_family=theme_plan.family.value,
            startup_mode=theme_plan.startup_mode,
            wallpapers=wallpapers,
            public_poster_path=poster_path,
            public_poster_included=True,
            photo_index_used=bool(resolved_photo_index and resolved_photo_index.photo_count > 0),
            private_selected_photos=photo_selections,
            fallback_reasons=fallback_reasons,
            public_monitor_uses_general_photos=False,
            display_1_source=(
                "approved_public_poster"
                if public_poster_path is not None
                else "placeholder_public_signal"
            ),
            monitor_mapping_source=monitor_mapping_source,
            role_mapping=role_mapping,
        )
        return self.manifest_store.save(manifest, output_dir / WALLPAPER_MANIFEST_NAME)

    def _monitor_mapping_reference(self) -> tuple[str, dict[str, str]]:
        config = self.monitor_mapping_store.load()
        if config is not None and config.assignments:
            return (
                "saved",
                {
                    role.value: assignment.display_label or assignment.stable_id
                    for role, assignment in config.assignments.items()
                },
            )
        layout = get_fallback_monitor_layout()
        return "fallback", role_mapping_for_manifest(layout)

    def _resolve_photo_index(
        self,
        photo_index: PhotoIndex | None,
        use_photo_index: bool,
    ) -> tuple[PhotoIndex | None, str | None]:
        if not use_photo_index:
            return None, None
        if photo_index is not None:
            return photo_index, None
        try:
            loaded = self.photo_indexer.load()
            if loaded is not None:
                return loaded, None
            if self.photo_indexer.source_exists():
                return self.photo_indexer.index(), None
            return None, None
        except (OSError, ValueError) as exc:
            return None, f"photo index unavailable: {exc}"

    def daily_seed(
        self,
        run_date: date,
        theme_plan: ThemePlan,
        role: str,
        regenerate_count: int = 0,
    ) -> int:
        seed_text = "|".join(
            (
                run_date.isoformat(),
                theme_plan.family.value,
                theme_plan.startup_mode,
                role,
                str(regenerate_count),
            )
        )
        digest = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
        return int(digest[:16], 16)

    def _output_dir(self, run_date: date, output_directory: Path | str | None = None) -> Path:
        if output_directory is not None:
            return get_generated_dir(run_date, output_directory)
        return get_generated_dir(run_date, self.base_path)
