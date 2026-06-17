"""Text-free generated art renderer for Display 1."""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from chaseos.models.poster import Display1ArtPlan, PublicPosterRenderResult
from chaseos.models.theme import ThemePlan
from chaseos.rendering._draw_utils import blend, hex_to_rgb, rgba

DISPLAY1_ART_SIZE = (1080, 1920)


class Display1ArtRenderer:
    """Render deterministic, text-free dusk cyberpunk art for Display 1."""

    def render(
        self,
        plan: Display1ArtPlan,
        image_path: Path,
        metadata_path: Path,
        theme_plan: ThemePlan | None = None,
    ) -> PublicPosterRenderResult:
        image_path.parent.mkdir(parents=True, exist_ok=True)
        rng = random.Random(plan.seed)
        palette = _palette(theme_plan, plan)
        image = Image.new("RGB", DISPLAY1_ART_SIZE, palette["sky_top"])
        draw = ImageDraw.Draw(image, "RGBA")

        self._sky_gradient(draw, palette)
        self._sun_disc(image, palette, plan.cyberpunk_intensity)
        towers = self._skyline_silhouette(draw, rng, palette, plan.cyberpunk_intensity)
        self._window_lights(draw, rng, towers, palette, plan.cyberpunk_intensity)
        self._haze(image, palette)
        if plan.show_geometry:
            self._geometry_overlay(draw, rng, palette, plan.cyberpunk_intensity)
        if plan.show_scanlines:
            self._scanlines(draw, palette, plan.cyberpunk_intensity)
        if plan.show_figure:
            self._figure(draw, palette)

        image.save(image_path, format="PNG")
        return PublicPosterRenderResult(
            image_path=image_path,
            metadata_path=metadata_path,
            width=DISPLAY1_ART_SIZE[0],
            height=DISPLAY1_ART_SIZE[1],
        )

    def _sky_gradient(
        self, draw: ImageDraw.ImageDraw, palette: dict[str, tuple[int, int, int]]
    ) -> None:
        width, height = DISPLAY1_ART_SIZE
        top = palette["sky_top"]
        mid = palette["sky_mid"]
        horizon = palette["horizon"]
        for y in range(height):
            p = y / (height - 1)
            color = (
                blend(top, mid, p / 0.72) if p < 0.72 else blend(mid, horizon, (p - 0.72) / 0.28)
            )
            draw.line((0, y, width, y), fill=color)

    def _sun_disc(
        self,
        image: Image.Image,
        palette: dict[str, tuple[int, int, int]],
        intensity: float,
    ) -> None:
        width, height = DISPLAY1_ART_SIZE
        cx = width // 2
        cy = int(height * 0.66)
        glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow, "RGBA")
        accent = palette["sun"]
        for radius, alpha in ((360, 22), (260, 34), (175, 52)):
            a = round(alpha + intensity * 24)
            glow_draw.ellipse(
                (cx - radius, cy - radius, cx + radius, cy + radius), fill=rgba(accent, a)
            )
        glow = glow.filter(ImageFilter.GaussianBlur(46))
        image.alpha_composite(glow) if image.mode == "RGBA" else image.paste(
            Image.alpha_composite(image.convert("RGBA"), glow).convert("RGB")
        )
        draw = ImageDraw.Draw(image, "RGBA")
        draw.ellipse((cx - 128, cy - 128, cx + 128, cy + 128), fill=rgba(accent, 215))
        draw.rectangle((0, cy + 24, width, cy + 170), fill=rgba(palette["horizon"], 140))

    def _skyline_silhouette(
        self,
        draw: ImageDraw.ImageDraw,
        rng: random.Random,
        palette: dict[str, tuple[int, int, int]],
        intensity: float,
    ) -> list[tuple[int, int, int, int]]:
        width, height = DISPLAY1_ART_SIZE
        base = height - 210
        distant = palette["distant_building"]
        foreground = palette["foreground_building"]
        towers: list[tuple[int, int, int, int]] = []

        x = -30
        while x < width + 30:
            w = rng.randint(36, 92)
            h = rng.randint(170, 520)
            top = base - h + rng.randint(-45, 55)
            rect = (x, top, x + w, height)
            draw.rectangle(rect, fill=rgba(distant, rng.randint(165, 210)))
            towers.append(rect)
            x += w + rng.randint(4, 18)

        for _ in range(rng.randint(2, 4)):
            w = rng.randint(115, 230)
            x = rng.randint(0, width - w)
            h = rng.randint(620, 1120)
            top = height - h
            rect = (x, top, x + w, height)
            draw.rectangle(rect, fill=rgba(foreground, 238))
            if intensity > 0.45:
                antenna_x = x + rng.randint(24, w - 24)
                draw.line(
                    (antenna_x, top, antenna_x, top - rng.randint(90, 180)),
                    fill=rgba(foreground, 220),
                    width=4,
                )
            towers.append(rect)
        return towers

    def _window_lights(
        self,
        draw: ImageDraw.ImageDraw,
        rng: random.Random,
        towers: list[tuple[int, int, int, int]],
        palette: dict[str, tuple[int, int, int]],
        intensity: float,
    ) -> None:
        warm = palette["warm_light"]
        cyan = palette["cyan_light"]
        density = 0.22 + intensity * 0.28
        for left, top, right, bottom in towers:
            if right - left < 28:
                continue
            y = max(top + 24, 260)
            while y < bottom - 120:
                x = left + 12
                while x < right - 14:
                    if rng.random() < density:
                        color = warm if rng.random() > 0.34 else cyan
                        ww = rng.randint(5, 16)
                        wh = rng.randint(8, 24)
                        draw.rectangle(
                            (x, y, x + ww, y + wh), fill=rgba(color, rng.randint(120, 220))
                        )
                    x += rng.randint(18, 34)
                y += rng.randint(28, 52)

    def _haze(self, image: Image.Image, palette: dict[str, tuple[int, int, int]]) -> None:
        width, height = DISPLAY1_ART_SIZE
        haze = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(haze, "RGBA")
        for y in range(int(height * 0.50), int(height * 0.82)):
            p = (y - height * 0.50) / (height * 0.32)
            alpha = round(80 * (1 - abs(p - 0.45)))
            draw.line((0, y, width, y), fill=rgba(palette["haze"], alpha))
        composited = Image.alpha_composite(image.convert("RGBA"), haze).convert("RGB")
        image.paste(composited)

    def _geometry_overlay(
        self,
        draw: ImageDraw.ImageDraw,
        rng: random.Random,
        palette: dict[str, tuple[int, int, int]],
        intensity: float,
    ) -> None:
        width, height = DISPLAY1_ART_SIZE
        alpha = round(28 + intensity * 74)
        primary = palette["geometry"]
        secondary = palette["cyan_light"]
        count = round(7 + intensity * 12)
        for _ in range(count):
            x = rng.randint(70, width - 70)
            y = rng.randint(110, height - 360)
            length = rng.randint(110, 360)
            mid = x + rng.choice((-1, 1)) * rng.randint(30, 90)
            end = mid + rng.choice((-1, 1)) * length
            color = primary if rng.random() > 0.45 else secondary
            draw.line(
                (x, y, mid, y, mid, y + rng.randint(-120, 120), end, y + rng.randint(-120, 120)),
                fill=rgba(color, alpha),
                width=2,
            )
            draw.ellipse((x - 5, y - 5, x + 5, y + 5), outline=rgba(color, alpha), width=2)
        for _ in range(3):
            size = rng.randint(140, 360)
            x = rng.randint(-80, width - 120)
            y = rng.randint(140, height - 520)
            draw.ellipse(
                (x, y, x + size, y + size), outline=rgba(primary, round(alpha * 0.55)), width=2
            )

    def _scanlines(
        self,
        draw: ImageDraw.ImageDraw,
        palette: dict[str, tuple[int, int, int]],
        intensity: float,
    ) -> None:
        width, height = DISPLAY1_ART_SIZE
        alpha = round(10 + intensity * 18)
        for y in range(0, height, 9):
            draw.line((0, y, width, y), fill=rgba(palette["sky_top"], alpha), width=1)

    def _figure(self, draw: ImageDraw.ImageDraw, palette: dict[str, tuple[int, int, int]]) -> None:
        x = DISPLAY1_ART_SIZE[0] // 2 + 210
        roof_y = DISPLAY1_ART_SIZE[1] - 385
        dark = palette["figure"]
        draw.rectangle((x - 70, roof_y + 88, x + 95, roof_y + 108), fill=rgba(dark, 235))
        draw.ellipse((x - 10, roof_y, x + 10, roof_y + 22), fill=rgba(dark, 245))
        draw.polygon(
            (
                (x - 17, roof_y + 24),
                (x + 17, roof_y + 24),
                (x + 25, roof_y + 82),
                (x - 22, roof_y + 82),
            ),
            fill=rgba(dark, 245),
        )
        draw.line((x - 8, roof_y + 80, x - 18, roof_y + 108), fill=rgba(dark, 245), width=6)
        draw.line((x + 8, roof_y + 80, x + 18, roof_y + 108), fill=rgba(dark, 245), width=6)


def _palette(
    theme_plan: ThemePlan | None, plan: Display1ArtPlan
) -> dict[str, tuple[int, int, int]]:
    if theme_plan is None:
        return _default_palette(plan.motif)
    colors = theme_plan.colors
    return {
        "sky_top": hex_to_rgb(colors.background),
        "sky_mid": hex_to_rgb(colors.surface),
        "horizon": hex_to_rgb(colors.primary),
        "sun": hex_to_rgb(colors.accent),
        "warm_light": hex_to_rgb(colors.text),
        "cyan_light": hex_to_rgb(colors.secondary),
        "geometry": hex_to_rgb(colors.accent),
        "haze": hex_to_rgb(colors.primary),
        "distant_building": blend(hex_to_rgb(colors.background), (0, 0, 0), 0.18),
        "foreground_building": blend(hex_to_rgb(colors.background), (0, 0, 0), 0.42),
        "figure": (5, 7, 12),
    }


def _default_palette(motif: str) -> dict[str, tuple[int, int, int]]:
    if motif == "mako_reactor":
        return {
            "sky_top": (8, 21, 33),
            "sky_mid": (17, 60, 62),
            "horizon": (73, 150, 105),
            "sun": (112, 230, 155),
            "warm_light": (237, 185, 86),
            "cyan_light": (67, 210, 205),
            "geometry": (87, 240, 177),
            "haze": (62, 140, 112),
            "distant_building": (10, 18, 24),
            "foreground_building": (3, 8, 13),
            "figure": (1, 5, 9),
        }
    if motif == "lofi_dusk":
        return {
            "sky_top": (24, 35, 65),
            "sky_mid": (74, 63, 96),
            "horizon": (207, 126, 85),
            "sun": (245, 122, 75),
            "warm_light": (245, 187, 95),
            "cyan_light": (92, 177, 194),
            "geometry": (232, 145, 118),
            "haze": (156, 103, 106),
            "distant_building": (20, 22, 35),
            "foreground_building": (8, 11, 22),
            "figure": (4, 7, 14),
        }
    return {
        "sky_top": (13, 18, 56),
        "sky_mid": (71, 32, 92),
        "horizon": (188, 70, 88),
        "sun": (235, 91, 57),
        "warm_light": (242, 180, 82),
        "cyan_light": (47, 202, 214),
        "geometry": (232, 79, 139),
        "haze": (144, 58, 98),
        "distant_building": (13, 17, 31),
        "foreground_building": (5, 7, 16),
        "figure": (2, 4, 9),
    }
