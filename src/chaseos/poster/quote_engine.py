"""Deterministic local quote generation for public innovation posters."""

from __future__ import annotations

from chaseos.poster.poster_safety import redact_sensitive_public_text, validate_public_text


class QuoteEngine:
    """Generate original short quotes from public-safe principles."""

    def generate_quote(
        self,
        public_safe_takeaway: str,
        change_requests: list[str] | tuple[str, ...] | None = None,
        regenerate_count: int = 0,
    ) -> str:
        changes = " ".join(change_requests or ()).lower()
        principle = redact_sensitive_public_text(public_safe_takeaway)

        if "less cheesy" in changes:
            options = (
                "Reusable structure beats repeated effort.",
                "Better inputs make faster fixes.",
                "Clear handoffs reduce repeated work.",
            )
        elif "quote shorter" in changes or "shorter" in changes:
            options = (
                "Clarity shortens the path.",
                "Build the shortcut.",
                "Make repetition easier.",
            )
        elif "more inspirational" in changes:
            options = (
                "Small fixes compound into calmer systems.",
                "Build the path before the rush.",
                "Service improves where friction becomes visible.",
            )
        else:
            lower = principle.lower()
            if "handoff" in lower:
                options = (
                    "A clearer handoff is a quieter day.",
                    "Clear handoffs reduce repeated work.",
                    "Build the path before the rush.",
                )
            elif "input" in lower or "faster fixes" in lower:
                options = (
                    "Better inputs make quieter fires.",
                    "Clarity shortens the path.",
                    "Better inputs make faster fixes.",
                )
            elif "repeated" in lower or "reusable" in lower:
                options = (
                    "Make the repeated thing easier.",
                    "Reusable structure beats repeated effort.",
                    "Find the pattern. Build the shortcut.",
                )
            else:
                options = (
                    "Turn friction into a system.",
                    "Service improves where friction becomes visible.",
                    "Small fixes compound into calmer systems.",
                )

        for offset in range(len(options)):
            quote = options[(regenerate_count + offset) % len(options)]
            if validate_public_text(quote):
                return quote
        return "Make the repeated thing easier."
