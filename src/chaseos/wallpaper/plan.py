"""Build and validate safe per-monitor wallpaper apply plans."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from chaseos.models.assets import GeneratedWallpaper, WallpaperManifest
from chaseos.models.monitor import MonitorLayout, MonitorRole
from chaseos.poster.poster_archive import POSTER_IMAGE_NAME, POSTER_METADATA_NAME, PosterArchive
from chaseos.storage.paths import get_chaseos_data_dir
from chaseos.wallpaper.photo_source import PhotoSourceConfig
from chaseos.wallpaper.wallpaper_manifest import WALLPAPER_MANIFEST_NAME, WallpaperManifestStore

ROLE_TO_DISPLAY_KEY = {
    MonitorRole.PUBLIC_SIGNAL: "display_1",
    MonitorRole.LEFT_ATMOSPHERE: "display_4",
    MonitorRole.CENTER_COMMAND: "display_2",
    MonitorRole.RIGHT_INSPIRATION: "display_3",
}
APPLY_ROLE_ALIASES = {
    MonitorRole.PUBLIC_SIGNAL: "public",
    MonitorRole.LEFT_ATMOSPHERE: "left",
    MonitorRole.CENTER_COMMAND: "center",
    MonitorRole.RIGHT_INSPIRATION: "right",
}
APPLY_ROLE_LABELS = {
    MonitorRole.PUBLIC_SIGNAL: "Public Signal Monitor",
    MonitorRole.LEFT_ATMOSPHERE: "Left Atmosphere Monitor",
    MonitorRole.CENTER_COMMAND: "Center Command Monitor",
    MonitorRole.RIGHT_INSPIRATION: "Right Inspiration Monitor",
}
REQUIRED_APPLY_ROLES = tuple(ROLE_TO_DISPLAY_KEY)


class WallpaperPlanError(ValueError):
    """Raised when ChaseOS cannot build a safe wallpaper apply plan."""


@dataclass(frozen=True)
class WallpaperTarget:
    role: str
    display_alias: str
    monitor_id: str
    label: str
    image_path: Path
    source: str


@dataclass(frozen=True)
class WallpaperApplyPlan:
    targets: tuple[WallpaperTarget, ...]
    generated_date: str
    mapping_source: str


class WallpaperApplyPlanner:
    """Resolve latest generated assets and monitor roles into apply targets."""

    def __init__(
        self,
        base_path: Path | str | None = None,
        photo_config: PhotoSourceConfig | None = None,
    ) -> None:
        self.base_path = Path(base_path) if base_path is not None else None
        self.photo_config = photo_config or PhotoSourceConfig()
        self.manifest_store = WallpaperManifestStore()
        self.poster_archive = PosterArchive()

    def build_plan(self, layout: MonitorLayout) -> WallpaperApplyPlan:
        manifest = self.latest_wallpaper_manifest()
        if manifest is None:
            raise WallpaperPlanError("no wallpaper manifest found. generate wallpapers first.")

        targets: list[WallpaperTarget] = []
        seen_roles: set[MonitorRole] = set()
        seen_monitors: set[str] = set()
        for role in REQUIRED_APPLY_ROLES:
            if role in seen_roles:
                raise WallpaperPlanError(f"duplicate role in apply plan: {role.value}")
            seen_roles.add(role)

            assignment = layout.assignments.get(role)
            if assignment is None:
                raise WallpaperPlanError(f"missing required role: {APPLY_ROLE_ALIASES[role]}")
            if assignment.stable_id in seen_monitors:
                raise WallpaperPlanError(
                    f"monitor {assignment.stable_id} is assigned to multiple roles"
                )
            seen_monitors.add(assignment.stable_id)

            image_path, source = self._image_for_role(role, manifest)
            if not image_path.exists():
                role_alias = APPLY_ROLE_ALIASES[role]
                raise WallpaperPlanError(f"missing image path for {role_alias}: {image_path}")
            if role == MonitorRole.PUBLIC_SIGNAL and self._is_general_photo_path(image_path):
                raise WallpaperPlanError("public role rejected a general local photo path")

            targets.append(
                WallpaperTarget(
                    role=APPLY_ROLE_ALIASES[role],
                    display_alias=assignment.display_label or assignment.stable_id,
                    monitor_id=assignment.stable_id,
                    label=APPLY_ROLE_LABELS[role],
                    image_path=image_path,
                    source=source,
                )
            )

        return WallpaperApplyPlan(
            targets=tuple(targets),
            generated_date=manifest.date.isoformat(),
            mapping_source=layout.source or manifest.monitor_mapping_source,
        )

    def latest_wallpaper_manifest(self) -> WallpaperManifest | None:
        generated_dir = get_chaseos_data_dir(self.base_path) / "generated"
        candidates = sorted(
            generated_dir.glob(f"*/{WALLPAPER_MANIFEST_NAME}"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for path in candidates:
            manifest = self.manifest_store.load(path)
            if manifest is not None:
                return manifest
        return None

    def latest_approved_public_poster(self) -> Path | None:
        posters_dir = get_chaseos_data_dir(self.base_path) / "posters"
        candidates = sorted(
            posters_dir.glob(f"*/{POSTER_METADATA_NAME}"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for metadata_path in candidates:
            metadata = self.poster_archive.load_metadata(metadata_path)
            if metadata is None or not metadata.approved:
                continue
            image_path = Path(metadata.image_path)
            if not image_path.is_absolute():
                image_path = metadata_path.parent / image_path
            if image_path.exists():
                return image_path
            fallback = metadata_path.parent / POSTER_IMAGE_NAME
            if fallback.exists():
                return fallback
        return None

    def _image_for_role(
        self,
        role: MonitorRole,
        manifest: WallpaperManifest,
    ) -> tuple[Path, str]:
        if role == MonitorRole.PUBLIC_SIGNAL:
            poster_path = self.latest_approved_public_poster()
            if poster_path is not None:
                return poster_path, "approved_public_poster"
            if manifest.public_poster_path is not None:
                return manifest.public_poster_path, manifest.display_1_source

        wallpaper = manifest.wallpapers.get(ROLE_TO_DISPLAY_KEY[role])
        if wallpaper is None:
            raise WallpaperPlanError(f"missing required role: {APPLY_ROLE_ALIASES[role]}")
        return wallpaper.image_path, self._source_for_wallpaper(wallpaper)

    def _source_for_wallpaper(self, wallpaper: GeneratedWallpaper) -> str:
        if wallpaper.selected_photo_path is not None:
            return wallpaper.source
        return wallpaper.generation_mode

    def _is_general_photo_path(self, image_path: Path) -> bool:
        candidates = (self.photo_config.source_path, Path(r"C:\_Media\Photos\Lightroom\Export"))
        try:
            resolved_image = image_path.resolve()
        except OSError:
            resolved_image = image_path.absolute()
        for source_path in candidates:
            try:
                resolved_source = source_path.resolve()
            except OSError:
                resolved_source = source_path.absolute()
            if resolved_image == resolved_source or resolved_source in resolved_image.parents:
                return True
        return False
