from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..config import get_auth_config
from ..services.quote_service import resolve_quote_of_the_day

bp = Blueprint("content", __name__)


def _database_url() -> str:
    return get_auth_config().database_url


@bp.get("/v1/content/quote-of-the-day")
def quote_of_the_day_route():
    language = request.args.get("lang", default="en", type=str)
    quote = resolve_quote_of_the_day(_database_url(), language=language)
    return jsonify({"quote": quote}), 200
