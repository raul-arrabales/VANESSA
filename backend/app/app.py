from __future__ import annotations

from flask import Flask

from .bootstrap import configure_request_context, register_http_blueprints, register_system_routes
from .config import AuthConfig, get_auth_config
from .db import get_connection
from .repositories.users import find_user_by_id
from .services.auth_runtime import ensure_auth_initialized
from .services.platform_service import get_active_capability_statuses
from .services.system_health import http_json_ok as _system_http_json_ok
from .services.system_health import postgres_ok as _system_postgres_ok

_ensure_auth_initialized = ensure_auth_initialized
_get_config = get_auth_config


def _http_json_ok(url: str) -> bool:
    return _system_http_json_ok(url, timeout_seconds=1.5)


def _postgres_ok(database_url: str) -> bool:
    return _system_postgres_ok(database_url, get_connection_fn=get_connection)


def create_app() -> Flask:
    app = Flask(__name__)
    configure_request_context(app)
    register_system_routes(app)
    register_http_blueprints(app)
    return app


app = create_app()
