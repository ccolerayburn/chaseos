"""Pillow renderer for the Display 1 public innovation poster."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from chaseos.models.poster import PublicPosterPlan, PublicPosterRenderResult
from chaseos.models.theme import ThemePlan

PUBLIC_POSTER_SIZE = (1080, 1920)

SAFE_MARGIN = 110


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def _blend(
    color_a: tuple[int, int, int],
    color_b: tuple[int, int, int],
    amount: float,
) -> tuple[int, int, int]:
    return tuple(round(a + ((b - a) * amount)) for a, b in zip(color_a, color_b, strict=True))


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        "CascadiaMono.ttf",
        "CascadiaCode.ttf",
        "consolab.ttf" if bold else "consola.ttf",
        "consola.ttf",
        "segoeui.ttf",
        "arial.ttf",
        r"C:\Windows\Fonts\CascadiaMono.ttf",
        r"C:\Windows\Fonts\CascadiaCode.ttf",
        r"C:\Windows\Fonts\consolab.ttf" if bold else r"C:\Windows\Fonts\consola.ttf",
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


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if _text_size(draw, candidate, font)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


class PublicPosterRenderer:
    """Render the public poster image using local Pillow drawing."""

    def render(
        self,
        plan: PublicPosterPlan,
        image_path: Path,
        metadata_path: Path,
        theme_plan: ThemePlan | None = None,
    ) -> PublicPosterRenderResult:
        image_path.parent.mkdir(parents=True, exist_ok=True)
        background = _hex_to_rgb(theme_plan.colors.background if theme_plan else "#151515")
        surface = _hex_to_rgb(theme_plan.colors.surface if theme_plan else "#232323")
        accent = _hex_to_rgb(theme_plan.colors.accent if theme_plan else "#b08a2e")
        text = _hex_to_rgb(theme_plan.colors.text if theme_plan else "#e0d2a0")
        secondary = _hex_to_rgb(theme_plan.colors.secondary if theme_plan else "#2f8f9d")

        width, height = PUBLIC_POSTER_SIZE
        image = Image.new("RGB", PUBLIC_POSTER_SIZE, background)
        draw = ImageDraw.Draw(image, "RGBA")

        for y in range(height):
            amount = y / height
            draw.line((0, y, width, y), fill=_blend(background, surface, amount * 0.75))

        self._draw_geometry(draw, plan, accent, secondary)
        self._draw_text(draw, plan, text, accent)

        image.save(image_path, format="PNG")
        return PublicPosterRenderResult(
            image_path=image_path,
            metadata_path=metadata_path,
            width=width,
            height=height,
        )

    def _draw_geometry(
        self,
        draw: ImageDraw.ImageDraw,
        plan: PublicPosterPlan,
        accent: tuple[int, int, int],
        secondary: tuple[int, int, int],
    ) -> None:
        width, height = PUBLIC_POSTER_SIZE
        density_step = 180 if plan.visual_density == "minimal" else 125
        dim_accent = (*accent, 80)
        dim_secondary = (*secondary, 65)

        for x in range(SAFE_MARGIN, width - SAFE_MARGIN, density_step):
            draw.line((x, 120, x, height - 140), fill=dim_secondary, width=1)
        for y in range(180, height - 180, density_step):
            draw.line((90, y, width - 90, y), fill=dim_secondary, width=1)

        draw.rectangle((72, 72, width - 72, height - 72), outline=dim_accent, width=2)
        draw.line((120, 260, width - 120, 180), fill=dim_accent, width=2)
        draw.line((150, height - 250, width - 150, height - 180), fill=dim_accent, width=2)

        if plan.cyberpunk_intensity > 0.55:
            draw.ellipse((760, 260, 1010, 510), outline=dim_accent, width=3)
            draw.rectangle((95, 1340, 290, 1530), outline=dim_secondary, width=2)

    def _draw_text(
        self,
        draw: ImageDraw.ImageDraw,
        plan: PublicPosterPlan,
        text_color: tuple[int, int, int],
        accent: tuple[int, int, int],
    ) -> None:
        width, height = PUBLIC_POSTER_SIZE
        quote_font = _font(82, bold=True)
        subtitle_font = _font(34)
        label_font = _font(24)

        quote = plan.quote.strip().strip('"')
        quote_lines = _wrap_text(draw, quote, quote_font, width - (SAFE_MARGIN * 2))
        line_height = max(_text_size(draw, "Ag", quote_font)[1] + 24, 90)
        total_height = len(quote_lines) * line_height
        y = (height // 2) - (total_height // 2) - 80

        for line in quote_lines:
            line_width, _ = _text_size(draw, line, quote_font)
            draw.text(((width - line_width) / 2, y), line, font=quote_font, fill=text_color)
            y += line_height

        if plan.subtitle:
            subtitle = plan.subtitle.upper()
            subtitle_width, _ = _text_size(draw, subtitle, subtitle_font)
            draw.text(
                ((width - subtitle_width) / 2, y + 40),
                subtitle,
                font=subtitle_font,
                fill=accent,
            )

        footer = f"{plan.style_family.value} / DISPLAY 1"
        footer_width, _ = _text_size(draw, footer, label_font)
        draw.text(
            ((width - footer_width) / 2, height - 160),
            footer,
            font=label_font,
            fill=accent,
        )
