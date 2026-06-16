"""Public poster safety and public-safe takeaway helpers."""

from __future__ import annotations

import re

PUBLIC_POSTER_SAFETY_RULES = (
    "never_include_private_checkin",
    "use_only_innovation_takeaway",
    "redact_sensitive_identifiers",
)

PUBLIC_REDACTION_TARGETS = (
    "ticket_numbers",
    "hostnames",
    "urls",
    "emails",
    "ip_addresses",
    "usernames",
    "company_names",
    "internal_systems",
    "credentials",
    "private_health_details",
)

DEFAULT_PUBLIC_DENYLIST = (
    "xray",
    "chase",
    "chaseos",
    "vpn",
    "active directory",
    "entra",
    "servicenow",
    "jira",
    "teams",
    "outlook",
    "hostname",
    "domain",
)

PRIVATE_HEALTH_TERMS = (
    "anxious",
    "anxiety",
    "depressed",
    "depression",
    "adhd",
    "headache",
    "migraine",
    "sleep",
    "slept",
    "tired",
    "exhausted",
    "hungry",
    "nauseous",
    "pain",
    "sick",
)


def redact_sensitive_public_text(
    text: str,
    denylist: tuple[str, ...] = DEFAULT_PUBLIC_DENYLIST,
) -> str:
    """Redact or generalize sensitive workplace/private content."""

    safe = text
    replacements = (
        (r"\b(?:INC|REQ|CHG|TASK)\d{5,}\b", "[ticket]"),
        (r"\b[A-Z]{2,}-\d{2,}\b", "[ticket]"),
        (r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "the right contact"),
        (r"https?://\S+|www\.\S+", "the workflow"),
        (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "the system"),
        (r"\b[A-Za-z]:\\[^\s]+", "the file path"),
        (r"\\\\[^\s\\]+\\[^\s]+", "the shared path"),
        (r"\b[A-Za-z0-9_.-]+\\[A-Za-z0-9_.-]+\b", "the right person"),
        (r"\b(?:api[_-]?key|token|secret|password)\s*[:=]\s*\S+", "[credential]"),
        (r"\b(?:server|host|hostname|machine)\s+[A-Za-z0-9_.-]+\b", "the system"),
        (r"\b[A-Za-z]{2,}[A-Za-z_-]*\d{2,}\b", "the system"),
    )
    for pattern, replacement in replacements:
        safe = re.sub(pattern, replacement, safe, flags=re.IGNORECASE)

    phrase_replacements = {
        "ticketing system": "workflow",
        "vpn tickets": "repeat access issues",
        "vpn": "access",
        "hostname and username": "the right details",
        "username and hostname": "the right details",
        "username": "the right details",
        "customer": "person",
        "queue": "workflow",
    }
    for phrase, replacement in phrase_replacements.items():
        safe = re.sub(rf"\b{re.escape(phrase)}\b", replacement, safe, flags=re.IGNORECASE)

    for term in denylist:
        replacement = "the workflow"
        if term in {"chase", "chaseos", "xray"}:
            replacement = "the work"
        if term in {"active directory", "entra", "domain"}:
            replacement = "access details"
        if term in {"teams", "outlook"}:
            replacement = "communication flow"
        safe = re.sub(rf"\b{re.escape(term)}\b", replacement, safe, flags=re.IGNORECASE)

    for term in PRIVATE_HEALTH_TERMS:
        safe = re.sub(rf"\b{re.escape(term)}\b", "private context", safe, flags=re.IGNORECASE)

    safe = re.sub(r"\s+", " ", safe)
    safe = re.sub(r"\s+([.,;:!?])", r"\1", safe)
    return safe.strip()


def public_safe_principle(private_takeaway: str) -> str:
    """Convert a private innovation takeaway into a public-safe principle."""

    sanitized = redact_sensitive_public_text(private_takeaway)
    lower = sanitized.lower()

    if any(word in lower for word in ("handoff", "escalation", "escalate")):
        return "Clear handoffs reduce repeated work."
    if any(word in lower for word in ("input", "details", "question", "questions", "ask")):
        return "Better inputs make faster fixes."
    if any(word in lower for word in ("repeat", "repeated", "same", "again", "reusable")):
        return "Repeated questions should become reusable structure."
    if any(word in lower for word in ("friction", "slow", "stuck", "messy")):
        return "Visible friction can become a cleaner path."
    if any(word in lower for word in ("workflow", "process", "system", "structure")):
        return "Turn friction into a system."

    words = [word for word in re.findall(r"[A-Za-z]+", sanitized) if len(word) > 2]
    if not words:
        return "Small improvements make work easier to repeat."
    return "Small improvements make repeated work easier."


def validate_public_text(
    text: str,
    raw_check_in: str | None = None,
    private_takeaway: str | None = None,
) -> bool:
    """Return True when public-facing text avoids private source strings."""

    lower = text.lower()
    if raw_check_in and raw_check_in.strip() and raw_check_in.lower() in lower:
        return False
    if private_takeaway and private_takeaway.strip() and private_takeaway.lower() in lower:
        return False
    sensitive_patterns = (
        r"\b(?:INC|REQ|CHG|TASK)\d{5,}\b",
        r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
        r"https?://\S+|www\.\S+",
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        r"\b(?:api[_-]?key|token|secret|password)\s*[:=]\s*\S+",
    )
    return not any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in sensitive_patterns)
