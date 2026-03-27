from __future__ import annotations

import pytest

from app.application import quote_management_service_app
from app.services.quote_management import QuoteValidationError


def test_list_quotes_maps_filter_validation_errors() -> None:
    with pytest.raises(quote_management_service_app.QuoteManagementRequestError) as exc_info:
        quote_management_service_app.list_quotes_response(
            "postgresql://ignored",
            args={},
            normalize_quote_filters_fn=lambda _args: (_ for _ in ()).throw(QuoteValidationError("invalid_boolean")),
        )

    assert exc_info.value.code == "invalid_boolean"
    assert exc_info.value.message == "Boolean filters must be true or false"


def test_create_quote_maps_duplicate_errors() -> None:
    with pytest.raises(quote_management_service_app.QuoteManagementRequestError) as exc_info:
        quote_management_service_app.create_quote_response(
            "postgresql://ignored",
            payload={"language": "en"},
            normalize_quote_payload_fn=lambda payload: payload,
            create_quote_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                quote_management_service_app.QuoteDuplicateError()
            ),
        )

    assert exc_info.value.code == "duplicate_quote"


def test_get_quote_maps_not_found_errors() -> None:
    with pytest.raises(quote_management_service_app.QuoteManagementRequestError) as exc_info:
        quote_management_service_app.get_quote_response(
            "postgresql://ignored",
            quote_id=17,
            get_quote_by_id_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                quote_management_service_app.QuoteNotFoundError()
            ),
        )

    assert exc_info.value.code == "quote_not_found"
