from chaseos.models.signals import PracticalSignals, StartupMode
from chaseos.poster.poster_safety import (
    PUBLIC_POSTER_SAFETY_RULES,
    public_safe_principle,
    redact_sensitive_public_text,
)
from chaseos.poster.public_poster_engine import PublicPosterEngine
from chaseos.theming.theme_generator import ThemeGenerator


def test_public_poster_rules_keep_private_checkin_out() -> None:
    assert "never_include_private_checkin" in PUBLIC_POSTER_SAFETY_RULES
    assert "use_only_innovation_takeaway" in PUBLIC_POSTER_SAFETY_RULES


def test_raw_checkin_text_is_not_used_in_public_poster_plan() -> None:
    theme = ThemeGenerator().generate(PracticalSignals(), StartupMode.STRUCTURED).plan
    plan = PublicPosterEngine().build_plan(
        innovation_exercise="10% Less Dumb",
        private_innovation_takeaway="We keep asking the same first questions manually.",
        theme_plan=theme,
        raw_check_in="slept bad and scattered",
    )
    plan_text = PublicPosterEngine().describe_plan(plan)

    assert "slept bad and scattered" not in plan_text


def test_emails_are_redacted_or_generalized() -> None:
    assert "person@example.com" not in redact_sensitive_public_text("Ask person@example.com")


def test_urls_are_redacted_or_generalized() -> None:
    text = redact_sensitive_public_text("Use https://internal.example.local/path")

    assert "https://" not in text


def test_ip_addresses_are_redacted_or_generalized() -> None:
    text = redact_sensitive_public_text("The host is 10.1.2.3")

    assert "10.1.2.3" not in text


def test_ticket_ids_are_redacted_or_generalized() -> None:
    text = redact_sensitive_public_text("INC0049217 showed the handoff is messy")

    assert "INC0049217" not in text


def test_hostnames_and_server_names_are_redacted_or_generalized() -> None:
    text = redact_sensitive_public_text("server abc01 needs hostname and username")

    assert "abc01" not in text
    assert "hostname" not in text.lower()
    assert "username" not in text.lower()


def test_file_paths_are_redacted_or_generalized() -> None:
    text = redact_sensitive_public_text(r"C:\Users\ccole\secret.txt has the answer")

    assert r"C:\Users" not in text


def test_obvious_secrets_are_redacted() -> None:
    text = redact_sensitive_public_text("token=abc123secret should not be public")

    assert "abc123secret" not in text


def test_private_health_details_are_not_in_public_safe_takeaway() -> None:
    principle = public_safe_principle("I had a headache and felt anxious about repeat work.")

    assert "headache" not in principle.lower()
    assert "anxious" not in principle.lower()


def test_public_safe_principle_is_non_empty() -> None:
    assert public_safe_principle("VPN tickets keep missing hostname and username")
