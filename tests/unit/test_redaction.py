from chaseos.poster.poster_safety import PUBLIC_REDACTION_TARGETS


def test_public_redaction_targets_include_sensitive_identifiers() -> None:
    assert "emails" in PUBLIC_REDACTION_TARGETS
    assert "ip_addresses" in PUBLIC_REDACTION_TARGETS
    assert "credentials" in PUBLIC_REDACTION_TARGETS

