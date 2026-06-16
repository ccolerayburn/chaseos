"""Private monitor local photo selection."""

from __future__ import annotations

from datetime import UTC, date, datetime
from math import sqrt

from chaseos.models.assets import PhotoAsset, PhotoIndex, PhotoOrientation, PhotoSelection
from chaseos.models.theme import PhotoUsage, ThemePlan
from chaseos.wallpaper.photo_source import PhotoSourceConfig

PRIVATE_DISPLAY_ROLES = {
    4: "left_atmosphere",
    2: "center_command",
    3: "right_inspiration",
}


class PhotoSelector:
    """Select private local photos for ChaseOS display roles."""

    def __init__(self, config: PhotoSourceConfig | None = None) -> None:
        self.config = config or PhotoSourceConfig()

    def select_for_private_displays(
        self,
        photo_index: PhotoIndex | None,
        theme_plan: ThemePlan,
        today: date | None = None,
        index_error: str | None = None,
    ) -> dict[str, PhotoSelection]:
        today = today or datetime.now(UTC).date()
        photos = photo_index.photos if photo_index is not None else []
        selections: dict[str, PhotoSelection] = {}

        for display_id, role in PRIVATE_DISPLAY_ROLES.items():
            display_key = f"display_{display_id}"
            mode = self._mode_for_display(theme_plan, display_id)
            if mode == PhotoUsage.GENERATED:
                selections[display_key] = PhotoSelection(
                    display_id=display_id,
                    display_key=display_key,
                    role=role,
                    mode=mode.value,
                    selection_reason="theme plan requested generated wallpaper",
                )
                continue

            if index_error:
                selections[display_key] = self._fallback(
                    display_id,
                    display_key,
                    role,
                    mode,
                    index_error,
                )
                continue

            candidates = self._rank_candidates(photos, theme_plan, today)
            if not candidates:
                selections[display_key] = self._fallback(
                    display_id,
                    display_key,
                    role,
                    mode,
                    "no valid local photos available",
                )
                continue

            selected = candidates[0]
            selections[display_key] = PhotoSelection(
                display_id=display_id,
                display_key=display_key,
                role=role,
                mode=mode.value,
                selected_photo_path=selected.path,
                selection_reason="selected private landscape photo compatible with theme palette",
            )

        return selections

    def _fallback(
        self,
        display_id: int,
        display_key: str,
        role: str,
        mode: PhotoUsage,
        reason: str,
    ) -> PhotoSelection:
        return PhotoSelection(
            display_id=display_id,
            display_key=display_key,
            role=role,
            mode=PhotoUsage.GENERATED.value,
            selection_reason=f"{mode.value} request fell back to generated wallpaper",
            fallback_used=True,
            fallback_reason=reason,
        )

    def _mode_for_display(self, theme_plan: ThemePlan, display_id: int) -> PhotoUsage:
        if display_id == 4:
            return theme_plan.local_photo_usage.display_4
        if display_id == 2:
            return theme_plan.local_photo_usage.display_2
        if display_id == 3:
            return theme_plan.local_photo_usage.display_3
        return PhotoUsage.GENERATED

    def _rank_candidates(
        self,
        photos: list[PhotoAsset],
        theme_plan: ThemePlan,
        today: date,
    ) -> list[PhotoAsset]:
        valid = [photo for photo in photos if photo.width > 0 and photo.height > 0]
        if not valid:
            return []

        non_recent = [photo for photo in valid if not self._is_recent(photo, today)]
        candidates = non_recent or valid
        return sorted(
            candidates,
            key=lambda photo: self._score(photo, theme_plan, today),
            reverse=True,
        )

    def _score(self, photo: PhotoAsset, theme_plan: ThemePlan, today: date) -> float:
        score = 0.0
        if photo.orientation == PhotoOrientation.LANDSCAPE:
            score += 42.0
        elif photo.orientation == PhotoOrientation.SQUARE:
            score += 12.0

        area = photo.width * photo.height
        score += min(20.0, area / (1920 * 1080) * 20.0)

        if 0.18 <= photo.brightness <= 0.82:
            score += 14.0
        else:
            score += 4.0

        if 0.06 <= photo.saturation <= 0.85:
            score += 10.0

        if not self._is_recent(photo, today):
            score += 28.0

        score += self._theme_color_score(photo, theme_plan) * 22.0
        return score

    def _is_recent(self, photo: PhotoAsset, today: date) -> bool:
        if photo.last_used_date is None:
            return False
        return (today - photo.last_used_date).days < self.config.avoid_repeats_days

    def _theme_color_score(self, photo: PhotoAsset, theme_plan: ThemePlan) -> float:
        photo_rgb = _hex_to_rgb(photo.average_color)
        palette = (
            _hex_to_rgb(theme_plan.colors.primary),
            _hex_to_rgb(theme_plan.colors.secondary),
            _hex_to_rgb(theme_plan.colors.accent),
        )
        distance = min(_color_distance(photo_rgb, color) for color in palette)
        maximum_distance = sqrt((255**2) * 3)
        return max(0.0, 1.0 - (distance / maximum_distance))


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) != 6:
        return (0, 0, 0)
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def _color_distance(
    color_a: tuple[int, int, int],
    color_b: tuple[int, int, int],
) -> float:
    return sqrt(sum((a - b) ** 2 for a, b in zip(color_a, color_b, strict=True)))
