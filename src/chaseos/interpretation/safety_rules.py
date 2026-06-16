"""Safety boundaries for check-in interpretation and public text."""

from __future__ import annotations

import re

PROHIBITED_CLINICAL_LABELS = (
    "adhd",
    "depression",
    "depressed",
    "anxiety",
    "anxious",
    "diagnosis",
    "diagnose",
    "disorder",
    "symptom",
    "symptoms",
    "screening",
    "score",
)

_REPLACEMENTS = {
    "adhd": "scattered focus",
    "depressed": "heavy mood",
    "depression": "heavy mood",
    "anxious": "under pressure",
    "anxiety": "pressure",
    "diagnosis": "practical read",
    "diagnose": "read",
    "disorder": "pattern",
    "symptoms": "signals",
    "symptom": "signal",
    "screening": "check-in",
    "score": "readout",
}


def contains_forbidden_clinical_text(text: str) -> bool:
    """Return whether terminal-facing text contains forbidden clinical labels."""

    lower = text.lower()
    return any(re.search(rf"\b{re.escape(term)}\b", lower) for term in PROHIBITED_CLINICAL_LABELS)


def ensure_non_clinical_text(text: str) -> str:
    """Rewrite forbidden labels into practical, non-clinical work-start language."""

    safe_text = text
    for term, replacement in _REPLACEMENTS.items():
        safe_text = re.sub(
            rf"\b{re.escape(term)}\b",
            replacement,
            safe_text,
            flags=re.IGNORECASE,
        )
    return safe_text
