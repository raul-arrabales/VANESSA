from __future__ import annotations

from datetime import date

import pytest

from app.services import quote_management


def test_normalize_quote_payload_requires_core_fields() -> None:
    with pytest.raises(ValueError) as exc_info:
        quote_management.normalize_quote_payload({"language": "en"})

    assert str(exc_info.value) == "invalid_text"


def test_normalize_quote_payload_normalizes_values() -> None:
    payload = quote_management.normalize_quote_payload({
        "language": " EN ",
        "text": " Keep steady. ",
        "author": " Vanessa ",
        "source_universe": " Original ",
        "tone": " Reflective ",
        "tags": [" AI ", "", "Ops"],
        "is_active": True,
        "is_approved": False,
        "origin": " LOCAL ",
        "external_ref": " ref-1 ",
    })

    assert payload == {
        "language": "en",
        "text": "Keep steady.",
        "author": "Vanessa",
        "source_universe": "Original",
        "tone": "reflective",
        "tags": ["ai", "ops"],
        "is_active": True,
        "is_approved": False,
        "origin": "local",
        "external_ref": "ref-1",
    }


def test_normalize_quote_filters_parses_query_values() -> None:
    filters = quote_management.normalize_quote_filters({
        "language": " ES ",
        "source_universe": "Original",
        "tone": "Funny",
        "origin": "Local",
        "is_active": "true",
        "is_approved": "false",
        "created_from": "2026-03-01",
        "created_to": "2026-03-31",
        "query": "galaxy",
    })

    assert filters["language"] == "es"
    assert filters["tone"] == "funny"
    assert filters["origin"] == "local"
    assert filters["is_active"] is True
    assert filters["is_approved"] is False
    assert filters["created_from"] == date(2026, 3, 1)
    assert filters["created_to"] == date(2026, 3, 31)
    assert filters["query"] == "galaxy"


def test_normalize_pagination_rejects_invalid_values() -> None:
    with pytest.raises(ValueError) as exc_info:
        quote_management.normalize_pagination("0", "10")

    assert str(exc_info.value) == "invalid_page"
