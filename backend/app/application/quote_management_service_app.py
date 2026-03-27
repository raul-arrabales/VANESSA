from __future__ import annotations

from typing import Any, Callable

from ..services.quote_management import (
    QuoteDuplicateError,
    QuoteNotFoundError,
    QuoteValidationError,
    create_quote as _create_quote,
    get_quote_by_id as _get_quote_by_id,
    get_quote_summary as _get_quote_summary,
    list_quotes as _list_quotes,
    normalize_pagination as _normalize_pagination,
    normalize_quote_filters as _normalize_quote_filters,
    normalize_quote_payload as _normalize_quote_payload,
    serialize_filters as _serialize_filters,
    serialize_quote as _serialize_quote,
    serialize_summary as _serialize_summary,
    update_quote as _update_quote,
)


class QuoteManagementRequestError(ValueError):
    def __init__(self, *, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _quote_filter_message(code: str) -> str:
    messages = {
        "invalid_boolean": "Boolean filters must be true or false",
        "invalid_date": "Date filters must use YYYY-MM-DD",
        "invalid_page": "page must be a positive integer",
        "invalid_page_size": "page_size must be between 1 and 100",
    }
    return messages.get(code, "Invalid quote filters")


def _quote_payload_message(code: str) -> str:
    return "Invalid quote payload"


def get_quote_summary_response(
    database_url: str,
    *,
    get_quote_summary_fn: Callable[[str], Any] = _get_quote_summary,
    serialize_summary_fn: Callable[[Any], dict[str, Any]] = _serialize_summary,
) -> dict[str, Any]:
    summary = get_quote_summary_fn(database_url)
    return {"summary": serialize_summary_fn(summary)}


def list_quotes_response(
    database_url: str,
    *,
    args: Any,
    normalize_quote_filters_fn: Callable[[Any], Any] = _normalize_quote_filters,
    normalize_pagination_fn: Callable[[str | None, str | None], tuple[int, int]] = _normalize_pagination,
    list_quotes_fn: Callable[..., Any] = _list_quotes,
    serialize_quote_fn: Callable[[Any], dict[str, Any]] = _serialize_quote,
    serialize_filters_fn: Callable[[Any], dict[str, Any]] = _serialize_filters,
) -> dict[str, Any]:
    try:
        filters = normalize_quote_filters_fn(args)
        page, page_size = normalize_pagination_fn(args.get("page"), args.get("page_size"))
    except QuoteValidationError as exc:
        raise QuoteManagementRequestError(
            status_code=400,
            code=exc.code,
            message=_quote_filter_message(exc.code),
        ) from exc

    result = list_quotes_fn(database_url, filters=filters, page=page, page_size=page_size)
    return {
        "items": [serialize_quote_fn(item) for item in result.items],
        "page": page,
        "page_size": page_size,
        "total": result.total,
        "filters": serialize_filters_fn(filters),
    }


def get_quote_response(
    database_url: str,
    *,
    quote_id: int,
    get_quote_by_id_fn: Callable[[str, int], Any] = _get_quote_by_id,
    serialize_quote_fn: Callable[[Any], dict[str, Any]] = _serialize_quote,
) -> dict[str, Any]:
    try:
        row = get_quote_by_id_fn(database_url, quote_id)
    except QuoteNotFoundError as exc:
        raise QuoteManagementRequestError(
            status_code=404,
            code="quote_not_found",
            message="Quote not found",
        ) from exc
    return {"quote": serialize_quote_fn(row)}


def create_quote_response(
    database_url: str,
    *,
    payload: Any,
    normalize_quote_payload_fn: Callable[[Any], Any] = _normalize_quote_payload,
    create_quote_fn: Callable[..., Any] = _create_quote,
    serialize_quote_fn: Callable[[Any], dict[str, Any]] = _serialize_quote,
) -> dict[str, Any]:
    try:
        normalized = normalize_quote_payload_fn(payload)
    except QuoteValidationError as exc:
        raise QuoteManagementRequestError(
            status_code=400,
            code=exc.code,
            message=_quote_payload_message(exc.code),
        ) from exc

    try:
        created = create_quote_fn(database_url, payload=normalized)
    except QuoteDuplicateError as exc:
        raise QuoteManagementRequestError(
            status_code=409,
            code="duplicate_quote",
            message="A quote with the same language and text already exists",
        ) from exc
    return {"quote": serialize_quote_fn(created)}


def update_quote_response(
    database_url: str,
    *,
    quote_id: int,
    payload: Any,
    normalize_quote_payload_fn: Callable[[Any], Any] = _normalize_quote_payload,
    update_quote_fn: Callable[..., Any] = _update_quote,
    serialize_quote_fn: Callable[[Any], dict[str, Any]] = _serialize_quote,
) -> dict[str, Any]:
    try:
        normalized = normalize_quote_payload_fn(payload)
    except QuoteValidationError as exc:
        raise QuoteManagementRequestError(
            status_code=400,
            code=exc.code,
            message=_quote_payload_message(exc.code),
        ) from exc

    try:
        updated = update_quote_fn(database_url, quote_id=quote_id, payload=normalized)
    except QuoteDuplicateError as exc:
        raise QuoteManagementRequestError(
            status_code=409,
            code="duplicate_quote",
            message="A quote with the same language and text already exists",
        ) from exc
    except QuoteNotFoundError as exc:
        raise QuoteManagementRequestError(
            status_code=404,
            code="quote_not_found",
            message="Quote not found",
        ) from exc
    return {"quote": serialize_quote_fn(updated)}
