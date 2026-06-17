from chaseos.poster.art_renderer import DISPLAY1_ART_SIZE
from chaseos.poster.poster_safety import PUBLIC_POSTER_SAFETY_RULES


def test_public_art_contract_is_present() -> None:
    assert DISPLAY1_ART_SIZE == (1080, 1920)
    assert "redact_sensitive_identifiers" in PUBLIC_POSTER_SAFETY_RULES
