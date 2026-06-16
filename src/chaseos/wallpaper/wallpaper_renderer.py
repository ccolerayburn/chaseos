"""Pillow renderer for private ChaseOS wallpapers."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps, UnidentifiedImageError

from chaseos.models.assets import GeneratedWallpaper
from chaseos.models.theme import ThemePlan, VisualDensity

WALLPAPER_ROLES = (
    "public_signal",
    "left_atmosphere",
    "center_command",
    "right_inspiration",
)

DEFAULT_WALLPAPER_SIZE = (1920, 1080)
PUBLIC_SIGNAL_SIZE = (1080, 1920)
WALLPAPER_STYLES = (
    "public_signal",
    "left_atmosphere",
    "center_command",
    "right_inspiration",
    "generated_minimal",
    "generated_cyberpunk",
    "command_grid",
    "atmosphere_gradient",
    "inspiration_geometry",
)


@dataclass(frozen=True)
class WallpaperRenderSpec:
    """Rendering request for one private wallpaper."""

    display_id: int
    role: str
    style: str
    width: int
    height: int
    output_path: Path
    seed: int
    photo_path: Path | None = None
    photo_mode: str = "generated"
    fallback_reason: str | None = None


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def _blend(
    color_a: tuple[int, int, int],
    color_b: tuple[int, int, int],
    amount: float,
) -> tuple[int, int, int]:
    return tuple(round(a + ((b - a) * amount)) for a, b in zip(color_a, color_b, strict=True))


def _rgba(color: tuple[int, int, int], alpha: int) -> tuple[int, int, int, int]:
    return (*color, alpha)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        "CascadiaMono.ttf",
        "CascadiaCode.ttf",
        "consola.ttf",
        "segoeui.ttf",
        "arial.ttf",
        r"C:\Windows\Fonts\CascadiaMono.ttf",
        r"C:\Windows\Fonts\CascadiaCode.ttf",
        r"C:\Windows\Fonts\consola.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _text_size(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


class WallpaperRenderer:
    """Render abstract wallpapers locally with Pillow."""

    def render(self, spec: WallpaperRenderSpec, theme_plan: ThemePlan) -> GeneratedWallpaper:
        spec.output_path.parent.mkdir(parents=True, exist_ok=True)
        rng = random.Random(spec.seed)
        background = _hex_to_rgb(theme_plan.colors.background)
        surface = _hex_to_rgb(theme_plan.colors.surface)
        primary = _hex_to_rgb(theme_plan.colors.primary)
        secondary = _hex_to_rgb(theme_plan.colors.secondary)
        accent = _hex_to_rgb(theme_plan.colors.accent)

        body_constrained = self._has_body_constraint(theme_plan)
        density = self._effective_density(theme_plan, spec.role, body_constrained)
        intensity = self._effective_intensity(theme_plan, spec.role, body_constrained)
        photo_used = False
        render_fallback_reason = spec.fallback_reason

        image = None
        if spec.photo_path is not None and spec.photo_mode in {"hybrid", "local_photo"}:
            image = self._photo_background(spec, background, accent)
            photo_used = image is not None
            if image is None:
                render_fallback_reason = (
                    render_fallback_reason
                    or "selected local photo unavailable; rendered generated wallpaper"
                )

        if image is None:
            image = Image.new("RGB", (spec.width, spec.height), background)
            draw = ImageDraw.Draw(image, "RGBA")
            self._gradient(draw, spec.width, spec.height, background, surface)
        else:
            draw = ImageDraw.Draw(image, "RGBA")
            self._draw_photo_linework(
                draw,
                spec,
                rng,
                primary,
                secondary,
                accent,
                density,
                intensity,
            )

        if photo_used:
            visual_noise = 0.14 if spec.role == "center_command" else 0.32
        elif spec.role == "public_signal":
            self._draw_public_signal(draw, spec, accent, text=theme_plan.colors.text)
            visual_noise = 0.18
        elif spec.role == "center_command":
            self._draw_center_command(draw, spec, secondary, accent, density, intensity)
            visual_noise = 0.12 if density == "very_sparse" else 0.18
        elif spec.role == "left_atmosphere":
            self._draw_left_atmosphere(
                draw,
                spec,
                rng,
                primary,
                secondary,
                accent,
                density,
                intensity,
            )
            visual_noise = 0.28 if density in {"very_sparse", "sparse"} else 0.42
        else:
            self._draw_right_inspiration(
                draw,
                spec,
                rng,
                primary,
                secondary,
                accent,
                density,
                intensity,
            )
            visual_noise = 0.34 if density in {"very_sparse", "sparse"} else 0.55

        image.save(spec.output_path, format="PNG")
        return GeneratedWallpaper(
            display_id=spec.display_id,
            role=spec.role,
            width=spec.width,
            height=spec.height,
            image_path=spec.output_path,
            generation_mode=spec.photo_mode if photo_used else spec.style,
            theme_family=theme_plan.family.value,
            created_at=datetime.now(UTC),
            public_safe=spec.role == "public_signal",
            source=(
                "local_photo_hybrid_no_text"
                if photo_used
                else "local_placeholder_public_signal"
                if spec.role == "public_signal"
                else "local_theme_geometry_no_text"
            ),
            visual_noise_score=visual_noise,
            selected_photo_path=spec.photo_path if photo_used else None,
            fallback_reason=render_fallback_reason,
        )

    def _photo_background(
        self,
        spec: WallpaperRenderSpec,
        background: tuple[int, int, int],
        accent: tuple[int, int, int],
    ) -> Image.Image | None:
        if spec.photo_path is None or not spec.photo_path.exists():
            return None
        try:
            with Image.open(spec.photo_path) as source:
                image = ImageOps.fit(
                    source.convert("RGB"),
                    (spec.width, spec.height),
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5),
                )
        except (OSError, UnidentifiedImageError, ValueError):
            return None

        local_photo = spec.photo_mode == "local_photo"
        if spec.role == "center_command":
            brightness = 0.48
            blend_amount = 0.56
        else:
            brightness = 0.74 if local_photo else 0.62
            blend_amount = 0.36 if local_photo else 0.48

        image = ImageEnhance.Brightness(image).enhance(brightness)
        image = ImageEnhance.Contrast(image).enhance(0.88)
        image = ImageEnhance.Color(image).enhance(0.82 if local_photo else 0.68)

        base = Image.new("RGB", (spec.width, spec.height), background)
        image = Image.blend(image, base, blend_amount)
        tinted = image.convert("RGBA")
        tint_alpha = 14 if spec.role == "center_command" else 24
        tint = Image.new("RGBA", (spec.width, spec.height), _rgba(accent, tint_alpha))
        return Image.alpha_composite(tinted, tint).convert("RGB")

    def _draw_photo_linework(
        self,
        draw: ImageDraw.ImageDraw,
        spec: WallpaperRenderSpec,
        rng: random.Random,
        primary: tuple[int, int, int],
        secondary: tuple[int, int, int],
        accent: tuple[int, int, int],
        density: str,
        intensity: float,
    ) -> None:
        width, height = spec.width, spec.height
        base_alpha = 18 if density == "very_sparse" else round(18 + (intensity * 34))

        if spec.role == "center_command":
            for x in range(120, width - 120, 240):
                draw.line((x, 70, x, 190), fill=_rgba(secondary, 20), width=1)
                draw.line((x, height - 190, x, height - 70), fill=_rgba(secondary, 20), width=1)
            draw.rounded_rectangle(
                (430, 260, width - 430, height - 260),
                radius=18,
                outline=_rgba(accent, 18),
                width=1,
            )
            return

        if spec.role == "left_atmosphere":
            for _ in range(5 if density in {"very_sparse", "sparse"} else 8):
                x = rng.randint(-120, width - 120)
                y = rng.randint(90, height - 90)
                draw.line(
                    (x, y, x + rng.randint(320, 760), y + rng.randint(-58, 58)),
                    fill=_rgba(primary if rng.random() > 0.45 else secondary, base_alpha),
                    width=2,
                )
            draw.line((0, height - 180, width, height - 280), fill=_rgba(accent, 22), width=2)
            return

        for _ in range(6 if density in {"very_sparse", "sparse"} else 10):
            size = rng.randint(72, 180)
            x = rng.randint(width // 3, width - size - 90)
            y = rng.randint(90, height - size - 90)
            color = accent if rng.random() > 0.5 else primary
            draw.rectangle((x, y, x + size, y + size), outline=_rgba(color, base_alpha), width=2)
        draw.arc((width - 520, -80, width + 80, 520), 90, 250, fill=_rgba(accent, 26), width=3)

    def _gradient(
        self,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        background: tuple[int, int, int],
        surface: tuple[int, int, int],
    ) -> None:
        for y in range(height):
            amount = y / height
            draw.line((0, y, width, y), fill=_blend(background, surface, amount * 0.65))

    def _draw_public_signal(
        self,
        draw: ImageDraw.ImageDraw,
        spec: WallpaperRenderSpec,
        accent: tuple[int, int, int],
        text: str,
    ) -> None:
        width, height = spec.width, spec.height
        text_color = _hex_to_rgb(text)
        title = "Daily Innovation Signal"
        title_font = _font(72)
        label_font = _font(24)

        for x in range(120, width - 120, 120):
            draw.line((x, 140, x, height - 140), fill=_rgba(accent, 36), width=1)
        draw.rectangle((80, 80, width - 80, height - 80), outline=_rgba(accent, 76), width=2)
        draw.line((140, 360, width - 140, 260), fill=_rgba(accent, 72), width=3)
        draw.line((140, height - 300, width - 140, height - 390), fill=_rgba(accent, 54), width=2)

        title_width, title_height = _text_size(draw, title, title_font)
        draw.text(
            ((width - title_width) / 2, (height - title_height) / 2),
            title,
            font=title_font,
            fill=text_color,
        )

        label = "DISPLAY 1 / PUBLIC SIGNAL"
        label_width, _ = _text_size(draw, label, label_font)
        draw.text(
            ((width - label_width) / 2, height - 170),
            label,
            font=label_font,
            fill=accent,
        )

    def _draw_center_command(
        self,
        draw: ImageDraw.ImageDraw,
        spec: WallpaperRenderSpec,
        secondary: tuple[int, int, int],
        accent: tuple[int, int, int],
        density: str,
        intensity: float,
    ) -> None:
        width, height = spec.width, spec.height
        edge_alpha = 34 if density == "very_sparse" else 48
        grid_step = 180 if density == "very_sparse" else 140
        for x in range(80, width - 80, grid_step):
            draw.line((x, 50, x, 230), fill=_rgba(secondary, edge_alpha), width=1)
            draw.line((x, height - 230, x, height - 50), fill=_rgba(secondary, edge_alpha), width=1)
        for y in range(70, height - 70, grid_step):
            draw.line((50, y, 280, y), fill=_rgba(secondary, edge_alpha), width=1)
            draw.line((width - 280, y, width - 50, y), fill=_rgba(secondary, edge_alpha), width=1)

        panel_alpha = 22 if intensity < 0.5 else 30
        draw.rounded_rectangle(
            (360, 220, width - 360, height - 220),
            radius=24,
            outline=_rgba(accent, panel_alpha),
            width=2,
        )
        draw.line((120, height - 120, width - 120, height - 120), fill=_rgba(accent, 34), width=2)

    def _draw_left_atmosphere(
        self,
        draw: ImageDraw.ImageDraw,
        spec: WallpaperRenderSpec,
        rng: random.Random,
        primary: tuple[int, int, int],
        secondary: tuple[int, int, int],
        accent: tuple[int, int, int],
        density: str,
        intensity: float,
    ) -> None:
        width, height = spec.width, spec.height
        count = {"very_sparse": 4, "sparse": 7, "medium": 13, "dense": 18}.get(density, 7)
        alpha = round(32 + (intensity * 70))
        for _ in range(count):
            x = rng.randint(-120, width)
            y = rng.randint(80, height - 80)
            length = rng.randint(260, 720)
            color = primary if rng.random() > 0.5 else secondary
            draw.line(
                (x, y, x + length, y + rng.randint(-80, 80)),
                fill=_rgba(color, alpha),
                width=2,
            )
        draw.ellipse((-260, 170, 420, 850), outline=_rgba(accent, 42), width=3)
        draw.line((0, height - 210, width, height - 320), fill=_rgba(secondary, 40), width=2)

    def _draw_right_inspiration(
        self,
        draw: ImageDraw.ImageDraw,
        spec: WallpaperRenderSpec,
        rng: random.Random,
        primary: tuple[int, int, int],
        secondary: tuple[int, int, int],
        accent: tuple[int, int, int],
        density: str,
        intensity: float,
    ) -> None:
        width, height = spec.width, spec.height
        count = {"very_sparse": 5, "sparse": 9, "medium": 18, "dense": 24}.get(density, 9)
        alpha = round(36 + (intensity * 85))
        for _ in range(count):
            x = rng.randint(220, width - 120)
            y = rng.randint(120, height - 120)
            size = rng.randint(60, 220)
            color = accent if rng.random() > 0.45 else primary
            draw.rectangle((x, y, x + size, y + size), outline=_rgba(color, alpha), width=2)
            draw.line(
                (x - 90, y + size // 2, x, y + size // 2),
                fill=_rgba(secondary, alpha),
                width=2,
            )
        draw.arc((width - 560, -120, width + 120, 560), 90, 260, fill=_rgba(accent, 56), width=4)
        draw.line((width - 640, height - 140, width - 100, 120), fill=_rgba(primary, 46), width=2)

    def _effective_density(self, theme_plan: ThemePlan, role: str, body_constrained: bool) -> str:
        if body_constrained:
            return "very_sparse"
        if role == "center_command":
            if theme_plan.visual_density == VisualDensity.VERY_SPARSE:
                return "very_sparse"
            return "sparse"
        return theme_plan.visual_density.value

    def _effective_intensity(
        self,
        theme_plan: ThemePlan,
        role: str,
        body_constrained: bool,
    ) -> float:
        intensity = theme_plan.cyberpunk_intensity
        if body_constrained:
            intensity = min(intensity, 0.25)
        if role == "center_command":
            intensity = min(intensity, 0.32)
        return intensity

    def _has_body_constraint(self, theme_plan: ThemePlan) -> bool:
        text = " ".join(theme_plan.notes).lower()
        return any(
            term in text
            for term in ("headache", "sensory", "low sleep", "fatigue", "body load")
        )
