from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..authz import require_role
from ..config import get_auth_config
from ..repositories.quote_management import (
    create_quote,
    get_quote_by_id,
    get_quote_summary,
    list_quotes,
    update_quote,
)
from ..services.quote_management import (
    normalize_pagination,
    normalize_quote_filters,
    normalize_quote_payload,
    serialize_quote,
)

bp = Blueprint("quotes_v1", __name__)


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


def _database_url() -> str:
    return get_auth_config().database_url


@bp.get("/v1/quotes/summary")
@require_role("admin")
def quote_summary_v1():
    summary = get_quote_summary(_database_url())
    return jsonify({"summary": summary}), 200


@bp.get("/v1/quotes")
@require_role("admin")
def quote_list_v1():
    try:
        filters = normalize_quote_filters(request.args)
        page, page_size = normalize_pagination(request.args.get("page"), request.args.get("page_size"))
    except ValueError as exc:
        code = str(exc)
        messages = {
            "invalid_boolean": "Boolean filters must be true or false",
            "invalid_date": "Date filters must use YYYY-MM-DD",
            "invalid_page": "page must be a positive integer",
            "invalid_page_size": "page_size must be between 1 and 100",
        }
        return _json_error(400, code, messages.get(code, "Invalid quote filters"))

    result = list_quotes(_database_url(), filters=filters, page=page, page_size=page_size)
    return jsonify({
        "items": [serialize_quote(item) for item in result["items"]],
        "page": page,
        "page_size": page_size,
        "total": result["total"],
        "filters": {
            key: value.isoformat() if hasattr(value, "isoformat") else value
            for key, value in filters.items()
            if value is not None
        },
    }), 200


@bp.get("/v1/quotes/<int:quote_id>")
@require_role("admin")
def get_quote_v1(quote_id: int):
    row = get_quote_by_id(_database_url(), quote_id)
    if row is None:
        return _json_error(404, "quote_not_found", "Quote not found")
    return jsonify({"quote": serialize_quote(row)}), 200


@bp.post("/v1/quotes")
@require_role("admin")
def create_quote_v1():
    try:
        normalized = normalize_quote_payload(request.get_json(silent=True))
    except ValueError as exc:
        code = str(exc)
        return _json_error(400, code, "Invalid quote payload")

    try:
        created = create_quote(_database_url(), payload=normalized)
    except Exception as exc:  # noqa: BLE001
        if "quotes_language_text_unique_idx" in str(exc) or "duplicate key value" in str(exc):
            return _json_error(409, "duplicate_quote", "A quote with the same language and text already exists")
        raise
    return jsonify({"quote": serialize_quote(created)}), 201


@bp.put("/v1/quotes/<int:quote_id>")
@require_role("admin")
def update_quote_v1(quote_id: int):
    try:
        normalized = normalize_quote_payload(request.get_json(silent=True))
    except ValueError as exc:
        code = str(exc)
        return _json_error(400, code, "Invalid quote payload")

    try:
        updated = update_quote(_database_url(), quote_id=quote_id, payload=normalized)
    except Exception as exc:  # noqa: BLE001
        if "quotes_language_text_unique_idx" in str(exc) or "duplicate key value" in str(exc):
            return _json_error(409, "duplicate_quote", "A quote with the same language and text already exists")
        raise
    if updated is None:
        return _json_error(404, "quote_not_found", "Quote not found")
    return jsonify({"quote": serialize_quote(updated)}), 200
