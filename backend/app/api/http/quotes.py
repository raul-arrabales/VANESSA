from __future__ import annotations

from flask import Blueprint, jsonify, request

from ...application.quote_management_service_app import (
    QuoteManagementRequestError,
    create_quote_response,
    get_quote_response,
    get_quote_summary_response,
    list_quotes_response,
    update_quote_response,
)
from ...authz import require_role
from ...config import get_auth_config
from ...services.quote_management import (
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

bp = Blueprint("quotes_v1", __name__)

get_quote_summary = _get_quote_summary
list_quotes = _list_quotes
get_quote_by_id = _get_quote_by_id
create_quote = _create_quote
update_quote = _update_quote
normalize_quote_filters = _normalize_quote_filters
normalize_pagination = _normalize_pagination
normalize_quote_payload = _normalize_quote_payload
serialize_quote = _serialize_quote
serialize_summary = _serialize_summary
serialize_filters = _serialize_filters


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


def _database_url() -> str:
    return get_auth_config().database_url


@bp.get("/v1/quotes/summary")
@require_role("admin")
def quote_summary_v1():
    payload = get_quote_summary_response(
        _database_url(),
        get_quote_summary_fn=get_quote_summary,
        serialize_summary_fn=serialize_summary,
    )
    return jsonify(payload), 200


@bp.get("/v1/quotes")
@require_role("admin")
def quote_list_v1():
    try:
        payload = list_quotes_response(
            _database_url(),
            args=request.args,
            normalize_quote_filters_fn=normalize_quote_filters,
            normalize_pagination_fn=normalize_pagination,
            list_quotes_fn=list_quotes,
            serialize_quote_fn=serialize_quote,
            serialize_filters_fn=serialize_filters,
        )
    except QuoteManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)

    return jsonify(payload), 200


@bp.get("/v1/quotes/<int:quote_id>")
@require_role("admin")
def get_quote_v1(quote_id: int):
    try:
        payload = get_quote_response(
            _database_url(),
            quote_id=quote_id,
            get_quote_by_id_fn=get_quote_by_id,
            serialize_quote_fn=serialize_quote,
        )
    except QuoteManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    return jsonify(payload), 200


@bp.post("/v1/quotes")
@require_role("admin")
def create_quote_v1():
    try:
        payload = create_quote_response(
            _database_url(),
            payload=request.get_json(silent=True),
            normalize_quote_payload_fn=normalize_quote_payload,
            create_quote_fn=create_quote,
            serialize_quote_fn=serialize_quote,
        )
    except QuoteManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    return jsonify(payload), 201


@bp.put("/v1/quotes/<int:quote_id>")
@require_role("admin")
def update_quote_v1(quote_id: int):
    try:
        payload = update_quote_response(
            _database_url(),
            quote_id=quote_id,
            payload=request.get_json(silent=True),
            normalize_quote_payload_fn=normalize_quote_payload,
            update_quote_fn=update_quote,
            serialize_quote_fn=serialize_quote,
        )
    except QuoteManagementRequestError as exc:
        return _json_error(exc.status_code, exc.code, exc.message)
    return jsonify(payload), 200


__all__ = [
    "bp",
    "_database_url",
    "_json_error",
    "get_quote_summary",
    "list_quotes",
    "get_quote_by_id",
    "create_quote",
    "update_quote",
    "normalize_quote_filters",
    "normalize_pagination",
    "normalize_quote_payload",
    "serialize_quote",
    "serialize_summary",
    "serialize_filters",
]
