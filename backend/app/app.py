from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from flask import Flask, Response, g, jsonify, request

from .auth_tokens import decode_access_token
from .config import AuthConfig
from .db import get_connection
from .repositories.users import find_user_by_id
from .services import auth_request_context, auth_runtime, system_health

app = Flask(__name__)

_DEFAULT_HTTP_TIMEOUT_SECONDS = 1.5
_GENERATED_DIR = Path(__file__).resolve().parent / "generated"
_ARCHITECTURE_JSON_PATH = _GENERATED_DIR / "architecture.json"
_ARCHITECTURE_SVG_PATH = _GENERATED_DIR / "architecture.svg"


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


def _http_json_ok(url: str) -> bool:
    return system_health.http_json_ok(url, timeout_seconds=_DEFAULT_HTTP_TIMEOUT_SECONDS)


def _load_architecture_payload() -> dict[str, Any]:
    return system_health.load_architecture_payload(_ARCHITECTURE_JSON_PATH)


def _postgres_ok(database_url: str) -> bool:
    return system_health.postgres_ok(database_url, get_connection_fn=get_connection)


def _get_config() -> AuthConfig:
    return auth_runtime.get_config()


def _ensure_auth_initialized() -> bool:
    return auth_runtime.ensure_auth_initialized()


@app.before_request
def load_current_user_from_token() -> None:
    g.current_user = None
    g.auth_error = None

    current_user, auth_error = auth_request_context.resolve_current_user_from_auth_header(
        request.headers.get("Authorization", ""),
        ensure_auth_initialized_fn=_ensure_auth_initialized,
        get_config_fn=_get_config,
        decode_access_token_fn=decode_access_token,
        find_user_by_id_fn=find_user_by_id,
    )
    g.current_user = current_user
    g.auth_error = auth_error


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "backend"}), 200


@app.get("/system/health")
def system_health_route():
    services = [
        {
            "service": "Frontend",
            "container": "frontend",
            "target": os.getenv("FRONTEND_URL", "http://frontend:3000"),
            "reachable": _http_json_ok(os.getenv("FRONTEND_URL", "http://frontend:3000").rstrip("/") + "/"),
        },
        {
            "service": "Backend",
            "container": "backend",
            "target": os.getenv("BACKEND_URL", "http://backend:5000"),
            "reachable": _http_json_ok(os.getenv("BACKEND_URL", "http://backend:5000").rstrip("/") + "/health"),
        },
        {
            "service": "LLM API",
            "container": "llm",
            "target": os.getenv("LLM_URL", "http://llm:8000"),
            "reachable": _http_json_ok(os.getenv("LLM_URL", "http://llm:8000").rstrip("/") + "/health"),
        },
        {
            "service": "LLM Runtime",
            "container": "llm_runtime",
            "target": os.getenv("LLM_RUNTIME_URL", "http://llm_runtime:8000"),
            "reachable": _http_json_ok(os.getenv("LLM_RUNTIME_URL", "http://llm_runtime:8000").rstrip("/") + "/health"),
        },
        {
            "service": "Agent Engine",
            "container": "agent_engine",
            "target": os.getenv("AGENT_ENGINE_URL", "http://agent_engine:7000"),
            "reachable": _http_json_ok(os.getenv("AGENT_ENGINE_URL", "http://agent_engine:7000").rstrip("/") + "/health"),
        },
        {
            "service": "Sandbox",
            "container": "sandbox",
            "target": os.getenv("SANDBOX_URL", "http://sandbox:6000"),
            "reachable": _http_json_ok(os.getenv("SANDBOX_URL", "http://sandbox:6000").rstrip("/") + "/health"),
        },
        {
            "service": "KWS",
            "container": "kws",
            "target": os.getenv("KWS_URL", "http://kws:10400"),
            "reachable": _http_json_ok(os.getenv("KWS_URL", "http://kws:10400").rstrip("/") + "/health"),
        },
        {
            "service": "Weaviate",
            "container": "weaviate",
            "target": os.getenv("WEAVIATE_URL", "http://weaviate:8080"),
            "reachable": _http_json_ok(
                os.getenv("WEAVIATE_URL", "http://weaviate:8080").rstrip("/") + "/v1/.well-known/ready"
            ),
        },
        {
            "service": "PostgreSQL",
            "container": "postgres",
            "target": "postgresql",
            "reachable": _postgres_ok(_get_config().database_url),
        },
    ]

    return (
        jsonify(
            {
                "status": "ok" if all(service["reachable"] for service in services) else "degraded",
                "services": services,
            }
        ),
        200,
    )


@app.get("/system/architecture")
def system_architecture():
    try:
        payload = _load_architecture_payload()
    except (FileNotFoundError, ValueError):
        return _json_error(
            503,
            "architecture_unavailable",
            "Architecture graph artifact not available. Run: python scripts/generate_architecture.py --write",
        )

    return jsonify(payload), 200


@app.get("/system/architecture.svg")
def system_architecture_svg():
    if not _ARCHITECTURE_SVG_PATH.exists():
        return _json_error(
            503,
            "architecture_unavailable",
            "Architecture SVG artifact not available. Run: python scripts/generate_architecture.py --write",
        )

    return Response(_ARCHITECTURE_SVG_PATH.read_text(encoding="utf-8"), mimetype="image/svg+xml")


# Register modular v1 blueprints.
from .routes import auth as auth_routes
from .routes import executions as executions_routes
from .routes import legacy_auth as legacy_auth_routes
from .routes import legacy_voice as legacy_voice_routes
from .routes import model_catalog_v1 as model_catalog_v1_routes
from .routes import model_governance as model_governance_routes
from .routes import model_inference_v1 as model_inference_v1_routes
from .routes import policy as policy_routes
from .routes import registry as registry_routes
from .routes import registry_models as registry_models_routes
from .routes import runtime as runtime_routes
from .routes import system as system_routes

app.register_blueprint(auth_routes.bp)
app.register_blueprint(system_routes.bp)
app.register_blueprint(registry_models_routes.bp)
app.register_blueprint(registry_routes.bp)
app.register_blueprint(policy_routes.bp)
app.register_blueprint(runtime_routes.bp)
app.register_blueprint(executions_routes.bp)
app.register_blueprint(model_governance_routes.bp)
app.register_blueprint(model_catalog_v1_routes.bp)
app.register_blueprint(model_inference_v1_routes.bp)
app.register_blueprint(legacy_auth_routes.bp)
app.register_blueprint(legacy_voice_routes.bp)
