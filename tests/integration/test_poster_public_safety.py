from chaseos.poster.poster_renderer import PUBLIC_POSTER_SIZE
from chaseos.poster.poster_safety import PUBLIC_POSTER_SAFETY_RULES


def test_public_poster_contract_is_present() -> None:
    assert PUBLIC_POSTER_SIZE == (1080, 1920)
    assert "redact_sensitive_identifiers" in PUBLIC_POSTER_SAFETY_RULES

