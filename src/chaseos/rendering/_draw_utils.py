"""Small color helpers shared by Pillow renderers."""

from __future__ import annotations


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def blend(
    color_a: tuple[int, int, int],
    color_b: tuple[int, int, int],
    amount: float,
) -> tuple[int, int, int]:
    amount = max(0.0, min(1.0, amount))
    return tuple(round(a + ((b - a) * amount)) for a, b in zip(color_a, color_b, strict=True))


def rgba(color: tuple[int, int, int], alpha: int) -> tuple[int, int, int, int]:
    return (*color, max(0, min(255, alpha)))
