from __future__ import annotations

from flask import Blueprint, jsonify, request

from ...config import get_auth_config
from ...services.quote_service import resolve_quote_of_the_day as _resolve_quote_of_the_day

bp = Blueprint("content", __name__)

resolve_quote_of_the_day = _resolve_quote_of_the_day


def _database_url() -> str:
    return get_auth_config().database_url


@bp.get("/v1/content/quote-of-the-day")
def quote_of_the_day_route():
    language = request.args.get("lang", default="en", type=str)
    selection_mode = request.args.get("selection", default="daily", type=str)
    if selection_mode not in {"daily", "random"}:
        selection_mode = "daily"
    quote = resolve_quote_of_the_day(_database_url(), language=language, selection_mode=selection_mode)
    return jsonify({"quote": quote}), 200


__all__ = [
    "bp",
    "_database_url",
    "resolve_quote_of_the_day",
]
