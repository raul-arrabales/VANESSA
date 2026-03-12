from __future__ import annotations

from datetime import date, datetime
from typing import Any

import psycopg

from ..repositories import quote_management as quote_repository
from .quote_management_types import (
    QuoteCountBucket,
    QuoteFilters,
    QuoteListResult,
    QuotePayload,
    QuoteRecord,
    QuoteSummary,
)


class QuoteValidationError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class QuoteDuplicateError(Exception):
    pass


class QuoteNotFoundError(Exception):
    pass


def parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise QuoteValidationError("invalid_boolean")


def normalize_date(value: str | None) -> date | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError as exc:
        raise QuoteValidationError("invalid_date") from exc


def normalize_pagination(page_raw: str | None, page_size_raw: str | None) -> tuple[int, int]:
    page = int(page_raw or "1")
    page_size = int(page_size_raw or "10")
    if page < 1:
        raise QuoteValidationError("invalid_page")
    if page_size < 1 or page_size > 100:
        raise QuoteValidationError("invalid_page_size")
    return page, page_size


def normalize_quote_filters(args: Any) -> QuoteFilters:
    return QuoteFilters(
        language=str(args.get("language", "")).strip().lower() or None,
        source_universe=str(args.get("source_universe", "")).strip() or None,
        tone=str(args.get("tone", "")).strip().lower() or None,
        origin=str(args.get("origin", "")).strip().lower() or None,
        is_active=parse_bool(args.get("is_active")),
        is_approved=parse_bool(args.get("is_approved")),
        created_from=normalize_date(args.get("created_from")),
        created_to=normalize_date(args.get("created_to")),
        query=str(args.get("query", "")).strip() or None,
    )


def normalize_quote_payload(payload: Any) -> QuotePayload:
    if not isinstance(payload, dict):
        raise QuoteValidationError("invalid_payload")

    language = str(payload.get("language", "")).strip().lower()
    text = str(payload.get("text", "")).strip()
    author = str(payload.get("author", "")).strip()
    source_universe = str(payload.get("source_universe", "")).strip()
    tone = str(payload.get("tone", "")).strip().lower()
    origin = str(payload.get("origin", "local")).strip().lower() or "local"
    external_ref = str(payload.get("external_ref", "")).strip() or None

    tags_raw = payload.get("tags", [])
    if not isinstance(tags_raw, list) or not all(isinstance(item, str) for item in tags_raw):
        raise QuoteValidationError("invalid_tags")
    tags = [item.strip().lower() for item in tags_raw if item.strip()]

    if not language:
        raise QuoteValidationError("invalid_language")
    if not text:
        raise QuoteValidationError("invalid_text")
    if not author:
        raise QuoteValidationError("invalid_author")
    if not source_universe:
        raise QuoteValidationError("invalid_source_universe")
    if not tone:
        raise QuoteValidationError("invalid_tone")
    if origin not in {"local", "cloud"}:
        raise QuoteValidationError("invalid_origin")

    is_active = payload.get("is_active", True)
    is_approved = payload.get("is_approved", True)
    if not isinstance(is_active, bool):
        raise QuoteValidationError("invalid_is_active")
    if not isinstance(is_approved, bool):
        raise QuoteValidationError("invalid_is_approved")

    return QuotePayload(
        language=language,
        text=text,
        author=author,
        source_universe=source_universe,
        tone=tone,
        tags=tags,
        is_active=is_active,
        is_approved=is_approved,
        origin=origin,
        external_ref=external_ref,
    )


def get_quote_summary(database_url: str) -> QuoteSummary:
    return quote_repository.get_quote_summary(database_url)


def list_quotes(
    database_url: str,
    *,
    filters: QuoteFilters,
    page: int,
    page_size: int,
) -> QuoteListResult:
    return quote_repository.list_quotes(database_url, filters=filters, page=page, page_size=page_size)


def get_quote_by_id(database_url: str, quote_id: int) -> QuoteRecord:
    row = quote_repository.get_quote_by_id(database_url, quote_id)
    if row is None:
        raise QuoteNotFoundError
    return row


def create_quote(database_url: str, *, payload: QuotePayload) -> QuoteRecord:
    try:
        return quote_repository.create_quote(database_url, payload=payload)
    except psycopg.IntegrityError as exc:
        if _is_duplicate_quote_error(exc):
            raise QuoteDuplicateError from exc
        raise


def update_quote(database_url: str, *, quote_id: int, payload: QuotePayload) -> QuoteRecord:
    try:
        updated = quote_repository.update_quote(database_url, quote_id=quote_id, payload=payload)
    except psycopg.IntegrityError as exc:
        if _is_duplicate_quote_error(exc):
            raise QuoteDuplicateError from exc
        raise
    if updated is None:
        raise QuoteNotFoundError
    return updated


def serialize_quote(row: QuoteRecord) -> dict[str, Any]:
    return {
        "id": row.id,
        "language": row.language,
        "text": row.text,
        "author": row.author,
        "source_universe": row.source_universe,
        "tone": row.tone,
        "tags": row.tags,
        "is_active": row.is_active,
        "is_approved": row.is_approved,
        "origin": row.origin,
        "external_ref": row.external_ref,
        "created_at": _serialize_datetime(row.created_at),
        "updated_at": _serialize_datetime(row.updated_at),
    }


def serialize_summary(summary: QuoteSummary) -> dict[str, Any]:
    return {
        "total": summary.total,
        "active": summary.active,
        "approved": summary.approved,
        "by_language": [{"value": item.value, "count": item.count} for item in summary.by_language],
        "by_tone": [{"value": item.value, "count": item.count} for item in summary.by_tone],
        "by_origin": [{"value": item.value, "count": item.count} for item in summary.by_origin],
    }


def serialize_filters(filters: QuoteFilters) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in vars(filters).items():
        if value is None:
            continue
        result[key] = value.isoformat() if isinstance(value, date) else value
    return result


def _serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _is_duplicate_quote_error(exc: psycopg.IntegrityError) -> bool:
    constraint_name = getattr(getattr(exc, "diag", None), "constraint_name", None)
    if constraint_name == "quotes_language_text_unique_idx":
        return True
    return "duplicate key value" in str(exc)
