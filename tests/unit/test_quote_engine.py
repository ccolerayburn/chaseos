from chaseos.poster.quote_engine import QuoteEngine


def test_quote_is_non_empty() -> None:
    quote = QuoteEngine().generate_quote("Repeated questions should become reusable structure.")

    assert quote


def test_quote_is_reasonably_short() -> None:
    quote = QuoteEngine().generate_quote("Repeated questions should become reusable structure.")

    assert 3 <= len(quote.split()) <= 12


def test_quote_does_not_include_sensitive_strings_from_private_takeaway() -> None:
    quote = QuoteEngine().generate_quote("Better inputs make faster fixes.")

    assert "INC0049217" not in quote
    assert "hostname" not in quote.lower()


def test_less_cheesy_request_returns_direct_quote() -> None:
    quote = QuoteEngine().generate_quote(
        "Repeated questions should become reusable structure.",
        change_requests=["less cheesy"],
    )

    assert quote in {
        "Reusable structure beats repeated effort.",
        "Better inputs make faster fixes.",
        "Clear handoffs reduce repeated work.",
    }


def test_quote_shorter_request_returns_short_quote() -> None:
    quote = QuoteEngine().generate_quote(
        "Repeated questions should become reusable structure.",
        change_requests=["quote shorter"],
    )

    assert len(quote.split()) <= 5

