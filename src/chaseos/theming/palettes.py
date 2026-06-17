"""Theme palette definitions."""

from __future__ import annotations

from chaseos.models.theme import ThemeColors, ThemeFamily

DEFAULT_TERMINAL_BACKGROUND = "#202020"
DEFAULT_TERMINAL_TEXT = "#b08a2e"


THEME_PALETTES = {
    ThemeFamily.OBSIDIAN_TERMINAL: {
        "label": "graphite / muted amber / deep cyan",
        "colors": ThemeColors(
            background="#171717",
            surface="#232323",
            primary="#b08a2e",
            secondary="#2f8f9d",
            accent="#6fb3bd",
            text="#c6a452",
        ),
    },
    ThemeFamily.NEON_NOIR: {
        "label": "black glass / violet magenta / electric cyan",
        "colors": ThemeColors(
            background="#151018",
            surface="#241b2a",
            primary="#c45cff",
            secondary="#1fb8d1",
            accent="#ff5aa8",
            text="#dfc7ff",
        ),
    },
    ThemeFamily.CHROME_MONOLITH: {
        "label": "charcoal / brushed steel / amber diode",
        "colors": ThemeColors(
            background="#181a1b",
            surface="#24282a",
            primary="#b7bdc2",
            secondary="#7a858c",
            accent="#c29b43",
            text="#d6d0bc",
        ),
    },
    ThemeFamily.VIOLET_CIRCUIT: {
        "label": "ink violet / muted amber / soft blue",
        "colors": ThemeColors(
            background="#171421",
            surface="#252136",
            primary="#9b7cff",
            secondary="#5f8ea0",
            accent="#d0a13a",
            text="#cfc6f2",
        ),
    },
    ThemeFamily.REDLINE_PROTOCOL: {
        "label": "carbon / dull red / warning amber",
        "colors": ThemeColors(
            background="#181414",
            surface="#292020",
            primary="#c44f46",
            secondary="#7c6b5a",
            accent="#d69d3f",
            text="#dbc4a2",
        ),
    },
    ThemeFamily.ARCTIC_INTERFACE: {
        "label": "deep gray / frost blue / quiet amber",
        "colors": ThemeColors(
            background="#181d20",
            surface="#242b2f",
            primary="#9db6c0",
            secondary="#5f7882",
            accent="#b89445",
            text="#ced8d8",
        ),
    },
    ThemeFamily.SYNTH_SANCTUARY: {
        "label": "warm graphite / dim gold / soft teal",
        "colors": ThemeColors(
            background="#1b1b19",
            surface="#262622",
            primary="#b79a55",
            secondary="#5f8b83",
            accent="#d2b46b",
            text="#d7ca9e",
        ),
    },
    ThemeFamily.SYNTHETIC_SUNRISE: {
        "label": "dark plum / muted gold / rose signal",
        "colors": ThemeColors(
            background="#1d171c",
            surface="#2b2329",
            primary="#c0a05c",
            secondary="#8b6e7d",
            accent="#d58c72",
            text="#dbc8b7",
        ),
    },
    ThemeFamily.DUSK_SKYLINE: {
        "label": "deep indigo / magenta dusk / amber cyan skyline",
        "colors": ThemeColors(
            background="#0d1238",
            surface="#47205c",
            primary="#bc4658",
            secondary="#2fcad6",
            accent="#eb5b39",
            text="#f2b452",
        ),
    },
    ThemeFamily.MAKO_REACTOR: {
        "label": "steel blue / mako teal / reactor amber",
        "colors": ThemeColors(
            background="#081521",
            surface="#113c3e",
            primary="#499669",
            secondary="#43d2cd",
            accent="#70e69b",
            text="#edb956",
        ),
    },
    ThemeFamily.LOFI_DUSK: {
        "label": "cool window dusk / lamp amber / soft rose",
        "colors": ThemeColors(
            background="#182341",
            surface="#4a3f60",
            primary="#cf7e55",
            secondary="#5cb1c2",
            accent="#f57a4b",
            text="#f5bb5f",
        ),
    },
}
