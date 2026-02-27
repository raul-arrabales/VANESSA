from __future__ import annotations

import os
import time
from json import dumps, loads
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from flask import Flask, Response, g, jsonify, request

from .auth_tokens import TOKEN_PREFIX, decode_access_token, issue_access_token
from .authz import AUTH_ROLES
from .config import AuthConfig, get_auth_config
from .db import get_connection, run_auth_schema_migration
from .repositories.model_assignments import list_scope_assignments, upsert_scope_assignment
from .repositories.model_catalog import (
    create_model_catalog_item,
    get_model_catalog_item,
    list_model_catalog,
    upsert_model_catalog_item,
)
from .repositories.model_download_jobs import (
    claim_next_queued_job,
    create_download_job,
    get_download_job,
    list_download_jobs,
    mark_job_failed,
    mark_job_succeeded,
    reconcile_stale_running_jobs,
)
from .repositories.model_access import (
    assign_model_access,
    find_model_definition,
    list_effective_allowed_models,
    register_model_definition,
)
from .services.hf_discovery import discover_hf_models, get_hf_model_details
from .services.model_downloader import download_from_huggingface, resolve_target_dir
from .services.runtime_profile_service import internet_allowed, resolve_runtime_profile
from .repositories.users import (
    activate_user,
    count_users_by_role,
    count_users,
    create_user,
    find_user_by_id,
    find_user_by_identifier,
    list_users,
    sanitize_user_record,
    update_user_role,
)
from .security import hash_password, verify_password

app = Flask(__name__)

_DEFAULT_COOLDOWN_MS = 2_000
_DEFAULT_DETECTION_THRESHOLD = 0.5
_DEFAULT_HTTP_TIMEOUT_SECONDS = 1.5
_MIN_PASSWORD_LENGTH = 8

_last_wake_by_key: dict[str, float] = {}
_seen_event_ids: dict[str, float] = {}

_DISCOVERY_LIMIT_MIN = 1
_DISCOVERY_LIMIT_MAX = 50
_GENERATED_DIR = Path(__file__).resolve().parent / "generated"
_ARCHITECTURE_JSON_PATH = _GENERATED_DIR / "architecture.json"
_ARCHITECTURE_SVG_PATH = _GENERATED_DIR / "architecture.svg"


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


def _legacy_models_response(payload: Any, status_code: int = 200):
    response = jsonify(payload)
    response.status_code = status_code
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "2026-12-31T00:00:00Z"
    response.headers["Link"] = '</v1/registry/models>; rel="successor-version"'
    return response


def _get_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _trim_seen_event_ids(max_age_seconds: float) -> None:
    cutoff = time.time() - max_age_seconds
    stale_ids = [
        event_id for event_id, seen_ts in _seen_event_ids.items() if seen_ts < cutoff
    ]
    for event_id in stale_ids:
        _seen_event_ids.pop(event_id, None)


def _http_json_ok(url: str) -> bool:
    from .services import system_health

    return system_health.http_json_ok(url, timeout_seconds=_DEFAULT_HTTP_TIMEOUT_SECONDS)


def _load_architecture_payload() -> dict[str, Any]:
    from .services import system_health

    return system_health.load_architecture_payload(_ARCHITECTURE_JSON_PATH)


def _postgres_ok(database_url: str) -> bool:
    from .services import system_health

    return system_health.postgres_ok(database_url, get_connection_fn=get_connection)


def _http_json_request(
    url: str, payload: dict[str, Any]
) -> tuple[dict[str, Any] | None, int]:
    req = Request(
        url,
        data=dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=_DEFAULT_HTTP_TIMEOUT_SECONDS) as response:
            status_code = int(response.status)
            body = response.read().decode("utf-8")
            return (loads(body) if body else {}), status_code
    except HTTPError as error:
        body = error.read().decode("utf-8")
        parsed = loads(body) if body else {"error": "upstream_error"}
        return parsed, int(error.code)
    except URLError:
        return None, 502


def _coerce_chat_messages(messages: Any) -> list[dict[str, Any]]:
    from .services import chat_inference

    return chat_inference.coerce_chat_messages(messages)


def _extract_output_text(llm_response: dict[str, Any]) -> str:
    from .services import chat_inference

    return chat_inference.extract_output_text(llm_response)


def _chat_completion_with_allowed_model(
    *,
    requested_model_id: str,
    org_id: str | None,
    group_id: str | None,
    messages: list[dict[str, Any]],
    max_tokens: int | None,
    temperature: float | None,
) -> tuple[dict[str, Any] | None, int]:
    from .services import chat_inference

    return chat_inference.chat_completion_with_allowed_model(
        requested_model_id=requested_model_id,
        org_id=org_id,
        group_id=group_id,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )


def _get_config() -> AuthConfig:
    from .services import auth_lifecycle

    return auth_lifecycle.get_config(get_auth_config)


def _bootstrap_superadmin(config: AuthConfig) -> None:
    from .services import auth_lifecycle

    auth_lifecycle.bootstrap_superadmin(
        config,
        count_users_fn=count_users,
        create_user_fn=create_user,
        hash_password_fn=hash_password,
    )


def _ensure_auth_initialized() -> bool:
    from .services import auth_lifecycle

    return auth_lifecycle.ensure_auth_initialized(
        app_logger=app.logger,
        get_config_fn=_get_config,
        run_auth_schema_migration_fn=run_auth_schema_migration,
        bootstrap_superadmin_fn=_bootstrap_superadmin,
        ensure_download_worker_started_fn=_ensure_download_worker_started,
    )


def _auth_ready_or_503():
    from .services import auth_lifecycle

    return auth_lifecycle.auth_ready_or_503(
        ensure_auth_initialized_fn=_ensure_auth_initialized,
        json_error_fn=_json_error,
    )


def _extract_register_actor() -> dict[str, Any] | None:
    actor = getattr(g, "current_user", None)
    if actor is None:
        return None
    return actor


def _validate_password_strength(password: str):
    if len(password) < _MIN_PASSWORD_LENGTH:
        return _json_error(
            422,
            "weak_password",
            f"Password must be at least {_MIN_PASSWORD_LENGTH} characters",
        )
    return None


def _serialize_model_definition(row: dict[str, Any]) -> dict[str, Any]:
    from .services import legacy_models_support

    return legacy_models_support.serialize_model_definition(row)


def _serialize_catalog_item(row: dict[str, Any]) -> dict[str, Any]:
    from .services import legacy_models_support

    return legacy_models_support.serialize_catalog_item(row)


def _serialize_assignment(row: dict[str, Any]) -> dict[str, Any]:
    from .services import legacy_models_support

    return legacy_models_support.serialize_assignment(row)


def _serialize_download_job(row: dict[str, Any]) -> dict[str, Any]:
    from .services import legacy_models_support

    return legacy_models_support.serialize_download_job(row)


def _parse_patterns(value: Any) -> list[str] | None:
    from .services import legacy_models_support

    return legacy_models_support.parse_patterns(value)


def _model_id_from_source(source_id: str) -> str:
    from .services import legacy_models_support

    return legacy_models_support.model_id_from_source(source_id)


def _download_worker_loop() -> None:
    from .services import model_download_worker

    model_download_worker.download_worker_loop()


def _ensure_download_worker_started() -> None:
    from .services import model_download_worker

    model_download_worker.ensure_download_worker_started()


def _effective_models_for_current_user(
    org_id: str | None, group_id: str | None
) -> list[dict[str, Any]]:
    return list_effective_allowed_models(
        _get_config().database_url,
        user_id=int(g.current_user["id"]),
        org_id=org_id,
        group_id=group_id,
    )


@app.before_request
def load_current_user_from_token() -> None:
    g.current_user = None
    g.auth_error = None

    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header:
        return

    prefix = f"{TOKEN_PREFIX} "
    if not auth_header.startswith(prefix):
        g.auth_error = "invalid_authorization_header"
        return

    token = auth_header[len(prefix) :].strip()
    if not token:
        g.auth_error = "missing_token"
        return

    if not _ensure_auth_initialized():
        g.auth_error = "auth_unavailable"
        return

    payload, error = decode_access_token(token, _get_config())
    if payload is None:
        g.auth_error = error or "invalid_token"
        return

    subject = str(payload.get("sub", "")).strip()
    if not subject.isdigit():
        g.auth_error = "invalid_token"
        return

    user = find_user_by_id(_get_config().database_url, int(subject))
    if user is None:
        g.auth_error = "invalid_token"
        return

    if not bool(user.get("is_active", False)):
        g.auth_error = "account_inactive"
        return

    g.current_user = user


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "backend"}), 200


@app.get("/system/health")
def system_health():
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


def register_user():
    from .handlers import legacy_auth

    return legacy_auth.register_user()


def login_user():
    from .handlers import legacy_auth

    return legacy_auth.login_user()


def logout_user():
    from .handlers import legacy_auth

    return legacy_auth.logout_user()


def auth_me():
    from .handlers import legacy_auth

    return legacy_auth.auth_me()


def activate_pending_user(user_id: int):
    from .handlers import legacy_auth

    return legacy_auth.activate_pending_user(user_id)


def auth_users_list():
    from .handlers import legacy_auth

    return legacy_auth.auth_users_list()


def update_role(user_id: int):
    from .handlers import legacy_auth

    return legacy_auth.update_role(user_id)


def admin_ping():
    from .handlers import legacy_auth

    return legacy_auth.admin_ping()


def superadmin_ping():
    from .handlers import legacy_auth

    return legacy_auth.superadmin_ping()


def get_models_catalog():
    from .handlers import legacy_models

    return legacy_models.get_models_catalog()


def create_models_catalog_item():
    from .handlers import legacy_models

    return legacy_models.create_models_catalog_item()


def get_models_assignments():
    from .handlers import legacy_models

    return legacy_models.get_models_assignments()


def put_models_assignment():
    from .handlers import legacy_models

    return legacy_models.put_models_assignment()


def discover_models_huggingface():
    from .handlers import legacy_models

    return legacy_models.discover_models_huggingface()


def get_discovered_model_huggingface(source_id: str):
    from .handlers import legacy_models

    return legacy_models.get_discovered_model_huggingface(source_id)


def start_model_download():
    from .handlers import legacy_models

    return legacy_models.start_model_download()


def get_model_download_jobs():
    from .handlers import legacy_models

    return legacy_models.get_model_download_jobs()


def get_model_download_job(job_id: str):
    from .handlers import legacy_models

    return legacy_models.get_model_download_job(job_id)


def register_model():
    from .handlers import legacy_models

    return legacy_models.register_model()


def assign_model():
    from .handlers import legacy_models

    return legacy_models.assign_model()


def get_allowed_models():
    from .handlers import legacy_models

    return legacy_models.get_allowed_models()


def get_enabled_models():
    from .handlers import legacy_models

    return legacy_models.get_enabled_models()


def generate_with_allowed_model():
    from .handlers import legacy_models

    return legacy_models.generate_with_allowed_model()


def inference_endpoint():
    from .handlers import legacy_models

    return legacy_models.inference_endpoint()


def wake_events():
    from .handlers import legacy_voice

    return legacy_voice.wake_events()


def voice_health():
    from .handlers import legacy_voice

    return legacy_voice.voice_health()


# Register modular v1 blueprints.
from .routes import auth as auth_routes
from .routes import executions as executions_routes
from .routes import legacy_auth as legacy_auth_routes
from .routes import legacy_models as legacy_models_routes
from .routes import legacy_voice as legacy_voice_routes
from .routes import policy as policy_routes
from .routes import registry as registry_routes
from .routes import runtime as runtime_routes
from .routes import system as system_routes

app.register_blueprint(auth_routes.bp)
app.register_blueprint(system_routes.bp)
app.register_blueprint(registry_routes.bp)
app.register_blueprint(policy_routes.bp)
app.register_blueprint(runtime_routes.bp)
app.register_blueprint(executions_routes.bp)
app.register_blueprint(legacy_auth_routes.bp)
app.register_blueprint(legacy_models_routes.bp)
app.register_blueprint(legacy_voice_routes.bp)
