from __future__ import annotations

import os
import threading
import time
from json import dumps, loads
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from flask import Flask, Response, g, jsonify, request

from .auth_tokens import TOKEN_PREFIX, decode_access_token, issue_access_token
from .authz import AUTH_ROLES, require_auth, require_role
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

_auth_config: AuthConfig | None = None
_auth_initialized = False
_auth_init_error: str | None = None
_download_worker_started = False
_download_worker_lock = threading.Lock()

_DOWNLOAD_POLL_SECONDS = 1.0
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
    req = Request(url, method="GET")
    try:
        with urlopen(req, timeout=_DEFAULT_HTTP_TIMEOUT_SECONDS) as response:
            return 200 <= response.status < 300
    except URLError:
        return False


def _load_architecture_payload() -> dict[str, Any]:
    if not _ARCHITECTURE_JSON_PATH.exists():
        raise FileNotFoundError(str(_ARCHITECTURE_JSON_PATH))
    raw_payload = _ARCHITECTURE_JSON_PATH.read_text(encoding="utf-8")
    parsed = loads(raw_payload)
    if not isinstance(parsed, dict):
        raise ValueError("Architecture payload must be a JSON object")
    return parsed


def _postgres_ok(database_url: str) -> bool:
    try:
        with get_connection(database_url) as connection:
            connection.execute("SELECT 1")
        return True
    except Exception:
        return False


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


def _http_get_json(url: str) -> tuple[dict[str, Any] | None, int]:
    req = Request(url, method="GET")
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
    if not isinstance(messages, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()
        if role not in {"system", "user", "assistant", "tool"}:
            continue
        if not content:
            continue
        normalized.append(
            {
                "role": role,
                "content": [{"type": "text", "text": content}],
            }
        )
    return normalized


def _extract_output_text(llm_response: dict[str, Any]) -> str:
    output = llm_response.get("output")
    if not isinstance(output, list) or len(output) == 0:
        return ""

    first = output[0]
    if not isinstance(first, dict):
        return ""
    content = first.get("content")
    if not isinstance(content, list) or len(content) == 0:
        return ""

    text_parts: list[str] = []
    for part in content:
        if isinstance(part, dict) and str(part.get("type", "")).lower() == "text":
            text = str(part.get("text", "")).strip()
            if text:
                text_parts.append(text)
    return "\n".join(text_parts)


def _chat_completion_with_allowed_model(
    *,
    requested_model_id: str,
    org_id: str | None,
    group_id: str | None,
    messages: list[dict[str, Any]],
    max_tokens: int | None,
    temperature: float | None,
) -> tuple[dict[str, Any] | None, int]:
    effective_models = _effective_models_for_current_user(org_id=org_id, group_id=group_id)
    allowed_model_ids = {str(model.get("model_id", "")) for model in effective_models}
    if requested_model_id not in allowed_model_ids:
        return {"error": "model_forbidden", "message": "Requested model is not allowed"}, 403

    llm_url = os.getenv("LLM_URL", "http://llm:8000").rstrip("/")
    upstream_payload: dict[str, Any] = {
        "model": requested_model_id,
        "input": messages,
    }
    if max_tokens is not None:
        upstream_payload["max_tokens"] = max_tokens
    if temperature is not None:
        upstream_payload["temperature"] = temperature

    return _http_json_request(f"{llm_url}/v1/chat/completions", upstream_payload)


def _get_config() -> AuthConfig:
    global _auth_config
    if _auth_config is None:
        _auth_config = get_auth_config()
    return _auth_config


def _bootstrap_superadmin(config: AuthConfig) -> None:
    existing_users = count_users(config.database_url)
    if existing_users > 0:
        return

    email = config.bootstrap_superadmin_email.strip().lower()
    username = config.bootstrap_superadmin_username.strip().lower()
    password = config.bootstrap_superadmin_password

    has_any_bootstrap_field = any([email, username, password])
    has_all_bootstrap_fields = bool(email and username and password)

    if has_any_bootstrap_field and not has_all_bootstrap_fields:
        print(
            "[WARN] Incomplete superadmin bootstrap env vars; skipping bootstrap user creation."
        )
        return

    if not has_all_bootstrap_fields:
        return

    create_user(
        config.database_url,
        email=email,
        username=username,
        password_hash=hash_password(password),
        role="superadmin",
        is_active=True,
    )
    print("[INFO] Bootstrap superadmin user created from environment.")


def _ensure_auth_initialized() -> bool:
    global _auth_initialized, _auth_init_error

    if _auth_initialized:
        return True
    if _auth_init_error is not None:
        return False

    try:
        config = _get_config()
        run_auth_schema_migration(config.database_url)
        _bootstrap_superadmin(config)
        _ensure_download_worker_started()
        _auth_initialized = True
        return True
    except Exception as exc:  # pragma: no cover - guarded by endpoint behavior tests
        _auth_init_error = str(exc)
        app.logger.error("Auth initialization failed: %s", exc)
        return False


def _auth_ready_or_503():
    if _ensure_auth_initialized():
        return None
    return _json_error(503, "auth_unavailable", "Authentication system unavailable")


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
    return {
        "model_id": row.get("model_id"),
        "provider": row.get("provider"),
        "metadata": row.get("metadata") or {},
        "provider_config_ref": row.get("provider_config_ref"),
    }


def _serialize_catalog_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("model_id"),
        "name": row.get("name"),
        "provider": row.get("provider"),
        "source_id": row.get("source_id"),
        "local_path": row.get("local_path"),
        "status": row.get("status"),
        "metadata": row.get("metadata") or {},
        "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
        "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
    }


def _serialize_assignment(row: dict[str, Any]) -> dict[str, Any]:
    model_ids_raw = row.get("model_ids") or []
    return {
        "scope": row.get("scope"),
        "model_ids": [str(item) for item in model_ids_raw if str(item).strip()],
    }


def _serialize_download_job(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": str(row.get("id")),
        "provider": row.get("provider"),
        "source_id": row.get("source_id"),
        "target_dir": row.get("target_dir"),
        "model_id": row.get("model_id"),
        "status": row.get("status"),
        "error_message": row.get("error_message"),
        "started_at": row.get("started_at").isoformat() if row.get("started_at") else None,
        "finished_at": row.get("finished_at").isoformat() if row.get("finished_at") else None,
        "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
        "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
    }


def _parse_patterns(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        patterns = [token.strip() for token in value.split(",") if token.strip()]
        return patterns if patterns else None
    if isinstance(value, list):
        patterns = [str(token).strip() for token in value if str(token).strip()]
        return patterns if patterns else None
    return None


def _model_id_from_source(source_id: str) -> str:
    return source_id.strip().replace("/", "--")


def _download_worker_loop() -> None:
    while True:
        try:
            config = _get_config()
            job = claim_next_queued_job(config.database_url)
            if job is None:
                time.sleep(_DOWNLOAD_POLL_SECONDS)
                continue

            allow_patterns = _parse_patterns(config.model_download_allow_patterns_default)
            ignore_patterns = _parse_patterns(config.model_download_ignore_patterns_default)
            source_id = str(job.get("source_id", ""))
            provider = str(job.get("provider", "huggingface"))
            model_id = _model_id_from_source(source_id)
            model_name = source_id.split("/")[-1] if "/" in source_id else source_id
            existing_model = get_model_catalog_item(config.database_url, model_id)
            if existing_model is not None:
                metadata = existing_model.get("metadata") if isinstance(existing_model.get("metadata"), dict) else {}
                allow_patterns = _parse_patterns(metadata.get("allow_patterns")) or allow_patterns
                ignore_patterns = _parse_patterns(metadata.get("ignore_patterns")) or ignore_patterns

            try:
                local_path = download_from_huggingface(
                    source_id=source_id,
                    storage_root=config.model_storage_root,
                    token=config.hf_token,
                    allow_patterns=allow_patterns,
                    ignore_patterns=ignore_patterns,
                )
            except Exception as exc:  # noqa: BLE001
                upsert_model_catalog_item(
                    config.database_url,
                    model_id=model_id,
                    name=model_name,
                    provider=provider,
                    source_id=source_id,
                    local_path=str(job.get("target_dir", "")) or None,
                    status="failed",
                    metadata={"source": "huggingface", "error": str(exc)},
                    updated_by_user_id=None,
                )
                mark_job_failed(
                    config.database_url,
                    job_id=str(job["id"]),
                    error_message=str(exc)[:2000],
                )
                continue

            upsert_model_catalog_item(
                config.database_url,
                model_id=model_id,
                name=model_name,
                provider=provider,
                source_id=source_id,
                local_path=local_path,
                status="available",
                metadata={"source": "huggingface"},
                updated_by_user_id=None,
            )
            mark_job_succeeded(
                config.database_url,
                job_id=str(job["id"]),
                model_id=model_id,
            )
        except Exception as exc:  # noqa: BLE001
            app.logger.error("Model download worker loop error: %s", exc)
            time.sleep(_DOWNLOAD_POLL_SECONDS)


def _ensure_download_worker_started() -> None:
    global _download_worker_started
    if _download_worker_started:
        return
    with _download_worker_lock:
        if _download_worker_started:
            return
        config = _get_config()
        reconcile_stale_running_jobs(
            config.database_url,
            stale_after_seconds=config.model_download_stale_seconds,
        )
        for index in range(config.model_download_max_workers):
            worker = threading.Thread(
                target=_download_worker_loop,
                name=f"model-download-worker-{index + 1}",
                daemon=True,
            )
            worker.start()
        _download_worker_started = True


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


@app.post("/auth/register")
def register_user():
    if (ready_error := _auth_ready_or_503()) is not None:
        return ready_error

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    email = str(payload.get("email", "")).strip().lower()
    username = str(payload.get("username", "")).strip().lower()
    password = str(payload.get("password", ""))
    requested_role_raw = payload.get("role")
    requested_role = (
        str(requested_role_raw).strip().lower()
        if requested_role_raw is not None
        else ""
    )
    requested_is_active = payload.get("is_active")

    if not email or "@" not in email:
        return _json_error(400, "invalid_email", "A valid email is required")
    if not username:
        return _json_error(400, "invalid_username", "Username is required")
    if not password:
        return _json_error(400, "invalid_password", "Password is required")

    if (password_error := _validate_password_strength(password)) is not None:
        return password_error

    actor = _extract_register_actor()
    role = "user"
    is_active = False

    if actor is None:
        if not _get_config().allow_self_register:
            return _json_error(
                403, "self_registration_disabled", "Self registration is disabled"
            )
        if requested_role and requested_role != "user":
            return _json_error(
                403, "role_assignment_forbidden", "Only superadmin can set custom role"
            )
        role = "user"
        is_active = False
    else:
        actor_role = str(actor.get("role", "user"))
        if actor_role == "superadmin":
            if requested_role and requested_role not in AUTH_ROLES:
                return _json_error(400, "invalid_role", "Invalid role value")
            role = requested_role or "user"
            if requested_is_active is None:
                is_active = role in {"admin", "superadmin"}
            else:
                is_active = bool(requested_is_active)
        elif actor_role == "admin":
            if requested_role and requested_role != "user":
                return _json_error(
                    403, "role_assignment_forbidden", "Admin can only create user role"
                )
            role = "user"
            is_active = False
        else:
            return _json_error(
                403, "insufficient_role", "Only admin or superadmin can create users"
            )

    try:
        created = create_user(
            _get_config().database_url,
            email=email,
            username=username,
            password_hash=hash_password(password),
            role=role,
            is_active=is_active,
        )
    except ValueError:
        return _json_error(409, "duplicate_user", "Email or username already exists")

    return jsonify({"user": sanitize_user_record(created)}), 201


@app.post("/auth/login")
def login_user():
    if (ready_error := _auth_ready_or_503()) is not None:
        return ready_error

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    identifier = str(
        payload.get("identifier")
        or payload.get("email")
        or payload.get("username")
        or ""
    ).strip()
    password = str(payload.get("password", ""))

    if not identifier or not password:
        return _json_error(
            400, "missing_credentials", "Identifier and password are required"
        )

    user = find_user_by_identifier(_get_config().database_url, identifier)
    if user is None:
        return _json_error(401, "invalid_credentials", "Invalid credentials")

    if not verify_password(password, str(user.get("password_hash", ""))):
        return _json_error(401, "invalid_credentials", "Invalid credentials")

    if not bool(user.get("is_active", False)):
        return _json_error(403, "account_inactive", "Account pending activation")

    token = issue_access_token(user, _get_config())
    return (
        jsonify(
            {
                "access_token": token,
                "token_type": "bearer",
                "expires_in": _get_config().access_token_ttl_seconds,
                "user": sanitize_user_record(user),
            }
        ),
        200,
    )


@app.post("/auth/logout")
@require_auth
def logout_user():
    return jsonify({"logged_out": True}), 200


@app.get("/auth/me")
@require_auth
def auth_me():
    return jsonify({"user": sanitize_user_record(g.current_user)}), 200


@app.post("/auth/users/<int:user_id>/activate")
@require_role("admin")
def activate_pending_user(user_id: int):
    if (ready_error := _auth_ready_or_503()) is not None:
        return ready_error

    target_user = find_user_by_id(_get_config().database_url, user_id)
    if target_user is None:
        return _json_error(404, "user_not_found", "User not found")

    actor_role = str(g.current_user.get("role", "user"))
    target_role = str(target_user.get("role", "user"))

    if actor_role == "admin" and target_role != "user":
        return _json_error(
            403, "insufficient_role", "Admin cannot activate elevated roles"
        )

    updated = activate_user(_get_config().database_url, user_id)
    if updated is None:
        return _json_error(404, "user_not_found", "User not found")

    return jsonify({"user": sanitize_user_record(updated)}), 200


@app.get("/auth/users")
@require_role("admin")
def auth_users_list():
    if (ready_error := _auth_ready_or_503()) is not None:
        return ready_error

    status = str(request.args.get("status", "")).strip().lower()
    if status and status not in {"pending", "active"}:
        return _json_error(
            400, "invalid_status", "status must be one of: pending, active"
        )

    active_filter: bool | None
    if status == "pending":
        active_filter = False
    elif status == "active":
        active_filter = True
    else:
        active_filter = None

    users = [
        sanitize_user_record(user)
        for user in list_users(_get_config().database_url, is_active=active_filter)
    ]
    return jsonify({"users": users}), 200


@app.patch("/auth/users/<int:user_id>/role")
@require_role("superadmin")
def update_role(user_id: int):
    if (ready_error := _auth_ready_or_503()) is not None:
        return ready_error

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    requested_role = str(payload.get("role", "")).strip().lower()
    if requested_role not in AUTH_ROLES:
        return _json_error(400, "invalid_role", "Invalid role value")

    target_user = find_user_by_id(_get_config().database_url, user_id)
    if target_user is None:
        return _json_error(404, "user_not_found", "User not found")

    target_role = str(target_user.get("role", "user"))
    if target_role == "superadmin" and requested_role != "superadmin":
        superadmin_count = count_users_by_role(_get_config().database_url, "superadmin")
        if superadmin_count <= 1:
            return _json_error(
                409,
                "last_superadmin_demote_forbidden",
                "Cannot demote the last remaining superadmin",
            )

    updated_user = update_user_role(_get_config().database_url, user_id, requested_role)
    if updated_user is None:
        return _json_error(404, "user_not_found", "User not found")

    return jsonify({"user": sanitize_user_record(updated_user)}), 200


@app.get("/admin/ping")
@require_role("admin")
def admin_ping():
    return jsonify({"status": "ok", "scope": "admin"}), 200


@app.get("/superadmin/ping")
@require_role("superadmin")
def superadmin_ping():
    return jsonify({"status": "ok", "scope": "superadmin"}), 200


@app.get("/models/catalog")
@require_role("superadmin")
def get_models_catalog():
    rows = list_model_catalog(_get_config().database_url)
    return _legacy_models_response({"models": [_serialize_catalog_item(row) for row in rows]}, 200)


@app.post("/models/catalog")
@require_role("superadmin")
def create_models_catalog_item():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    name = str(payload.get("name", "")).strip()
    provider = str(payload.get("provider", "custom")).strip().lower() or "custom"
    source_id = str(payload.get("source_id", "")).strip() or None
    local_path = str(payload.get("local_path", "")).strip() or None
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}

    if not name:
        return _json_error(400, "invalid_name", "name is required")
    if provider not in {"huggingface", "local", "custom"}:
        return _json_error(400, "invalid_provider", "provider must be huggingface, local, or custom")
    if provider == "local" and not local_path:
        return _json_error(400, "invalid_local_path", "local_path is required for local provider")
    if provider == "local" and local_path:
        storage_root = Path(_get_config().model_storage_root).resolve()
        candidate = Path(local_path).expanduser()
        if not candidate.is_absolute():
            candidate = storage_root / candidate
        candidate_resolved = candidate.resolve()
        if storage_root != candidate_resolved and storage_root not in candidate_resolved.parents:
            return _json_error(400, "invalid_local_path", "local_path must be under MODEL_STORAGE_ROOT")
        local_path = str(candidate_resolved)

    model_id = str(payload.get("id", "")).strip() or _model_id_from_source(source_id or name.lower().replace(" ", "-"))

    if provider == "huggingface" and source_id:
        try:
            resolved_local_path = resolve_target_dir(_get_config().model_storage_root, source_id)
            if local_path is None:
                local_path = resolved_local_path
        except ValueError:
            return _json_error(400, "invalid_source_id", "Invalid source_id")

    try:
        created = create_model_catalog_item(
            _get_config().database_url,
            model_id=model_id,
            name=name,
            provider=provider,
            source_id=source_id,
            local_path=local_path,
            status=str(payload.get("status", "available")),
            metadata=metadata,
            created_by_user_id=int(g.current_user["id"]),
        )
    except ValueError as exc:
        code = str(exc)
        if code == "duplicate_model":
            return _json_error(409, "duplicate_model", "model id already exists")
        return _json_error(400, code, "Invalid model catalog payload")

    return _legacy_models_response({"model": _serialize_catalog_item(created)}, 201)


@app.get("/models/assignments")
@require_role("admin")
def get_models_assignments():
    rows = list_scope_assignments(_get_config().database_url)
    return _legacy_models_response({"assignments": [_serialize_assignment(row) for row in rows]}, 200)


@app.put("/models/assignments")
@require_role("admin")
def put_models_assignment():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    scope = str(payload.get("scope", "")).strip().lower()
    model_ids = payload.get("model_ids")
    if not isinstance(model_ids, list):
        return _json_error(400, "invalid_model_ids", "model_ids must be an array")

    try:
        saved = upsert_scope_assignment(
            _get_config().database_url,
            scope=scope,
            model_ids=[str(item) for item in model_ids],
            updated_by_user_id=int(g.current_user["id"]),
        )
    except ValueError:
        return _json_error(400, "invalid_scope", "scope must be user, admin, or superadmin")

    return _legacy_models_response({"assignment": _serialize_assignment(saved)}, 200)


@app.get("/models/discovery/huggingface")
@require_role("superadmin")
def discover_models_huggingface():
    runtime_profile = resolve_runtime_profile(_get_config().database_url)
    if not internet_allowed(runtime_profile):
        return _json_error(
            403,
            "runtime_profile_blocks_internet",
            f"Model discovery disabled for runtime profile '{runtime_profile}'",
        )

    query = str(request.args.get("query", "")).strip()
    task = str(request.args.get("task", "text-generation")).strip() or "text-generation"
    sort = str(request.args.get("sort", "downloads")).strip() or "downloads"
    limit_raw = str(request.args.get("limit", "10")).strip()
    try:
        limit = int(limit_raw)
    except ValueError:
        return _json_error(400, "invalid_limit", "limit must be an integer")
    limit = max(_DISCOVERY_LIMIT_MIN, min(_DISCOVERY_LIMIT_MAX, limit))

    try:
        models = discover_hf_models(
            query=query,
            task=task,
            sort=sort,
            limit=limit,
            token=_get_config().hf_token,
        )
    except Exception as exc:  # noqa: BLE001
        return _json_error(502, "hf_discovery_failed", str(exc))

    return _legacy_models_response({"models": models}, 200)


@app.get("/models/discovery/huggingface/<path:source_id>")
@require_role("superadmin")
def get_discovered_model_huggingface(source_id: str):
    runtime_profile = resolve_runtime_profile(_get_config().database_url)
    if not internet_allowed(runtime_profile):
        return _json_error(
            403,
            "runtime_profile_blocks_internet",
            f"Model discovery disabled for runtime profile '{runtime_profile}'",
        )

    if not source_id.strip():
        return _json_error(400, "invalid_source_id", "source_id is required")
    try:
        model = get_hf_model_details(source_id.strip(), token=_get_config().hf_token)
    except Exception as exc:  # noqa: BLE001
        return _json_error(502, "hf_model_info_failed", str(exc))
    return _legacy_models_response({"model": model}, 200)


@app.post("/models/catalog/downloads")
@require_role("superadmin")
def start_model_download():
    runtime_profile = resolve_runtime_profile(_get_config().database_url)
    if not internet_allowed(runtime_profile):
        return _json_error(
            403,
            "runtime_profile_blocks_internet",
            f"Model download disabled for runtime profile '{runtime_profile}'",
        )

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    source_id = str(payload.get("source_id", "")).strip()
    if not source_id:
        return _json_error(400, "invalid_source_id", "source_id is required")

    allow_patterns = _parse_patterns(payload.get("allow_patterns"))
    ignore_patterns = _parse_patterns(payload.get("ignore_patterns"))

    config = _get_config()
    try:
        target_dir = resolve_target_dir(config.model_storage_root, source_id)
    except ValueError:
        return _json_error(400, "invalid_source_id", "Invalid source_id")

    model_id = _model_id_from_source(source_id)
    display_name = str(payload.get("name", "")).strip() or source_id.split("/")[-1]

    upsert_model_catalog_item(
        config.database_url,
        model_id=model_id,
        name=display_name,
        provider="huggingface",
        source_id=source_id,
        local_path=target_dir,
        status="downloading",
        metadata={
            "source": "huggingface",
            "allow_patterns": allow_patterns or _parse_patterns(config.model_download_allow_patterns_default) or [],
            "ignore_patterns": ignore_patterns or _parse_patterns(config.model_download_ignore_patterns_default) or [],
        },
        updated_by_user_id=int(g.current_user["id"]),
    )

    job_id = uuid4()
    created = create_download_job(
        config.database_url,
        job_id=job_id,
        provider="huggingface",
        source_id=source_id,
        target_dir=target_dir,
        created_by_user_id=int(g.current_user["id"]),
    )
    _ensure_download_worker_started()
    return _legacy_models_response({"job": _serialize_download_job(created)}, 202)


@app.get("/models/catalog/downloads")
@require_role("superadmin")
def get_model_download_jobs():
    status = str(request.args.get("status", "")).strip().lower() or None
    rows = list_download_jobs(_get_config().database_url, status=status, limit=50)
    return _legacy_models_response({"jobs": [_serialize_download_job(row) for row in rows]}, 200)


@app.get("/models/catalog/downloads/<job_id>")
@require_role("superadmin")
def get_model_download_job(job_id: str):
    row = get_download_job(_get_config().database_url, job_id)
    if row is None:
        return _json_error(404, "download_job_not_found", "Download job not found")
    return _legacy_models_response({"job": _serialize_download_job(row)}, 200)


@app.post("/models/registry")
@require_role("superadmin")
def register_model():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    model_id = str(payload.get("model_id", "")).strip()
    provider = str(payload.get("provider", "")).strip()
    metadata = payload.get("metadata")
    provider_config_ref = payload.get("provider_config_ref")

    if not model_id:
        return _json_error(400, "invalid_model_id", "model_id is required")
    if not provider:
        return _json_error(400, "invalid_provider", "provider is required")
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        return _json_error(400, "invalid_metadata", "metadata must be an object")

    try:
        created = register_model_definition(
            _get_config().database_url,
            model_id=model_id,
            provider=provider,
            metadata=metadata,
            provider_config_ref=(
                str(provider_config_ref).strip()
                if provider_config_ref is not None
                else None
            ),
            created_by_user_id=int(g.current_user["id"]),
        )
    except ValueError:
        return _json_error(409, "duplicate_model", "model_id already exists")
    return jsonify({"model": _serialize_model_definition(created)}), 201


@app.post("/models/access-assignments")
@require_role("admin")
def assign_model():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    model_id = str(payload.get("model_id", "")).strip()
    scope_type = str(payload.get("scope_type", "")).strip().lower()
    scope_id = str(payload.get("scope_id", "")).strip()
    if not model_id:
        return _json_error(400, "invalid_model_id", "model_id is required")
    if scope_type not in {"org", "group", "user"}:
        return _json_error(
            400, "invalid_scope_type", "scope_type must be org, group, or user"
        )
    if not scope_id:
        return _json_error(400, "invalid_scope_id", "scope_id is required")

    if find_model_definition(_get_config().database_url, model_id) is None:
        return _json_error(404, "model_not_found", "Model definition not found")

    assigned = assign_model_access(
        _get_config().database_url,
        model_id=model_id,
        scope_type=scope_type,
        scope_id=scope_id,
        assigned_by_user_id=int(g.current_user["id"]),
    )
    return (
        jsonify(
            {
                "assignment": {
                    "model_id": assigned["model_id"],
                    "scope_type": assigned["scope_type"],
                    "scope_id": assigned["scope_id"],
                }
            }
        ),
        201,
    )


@app.get("/models/allowed")
@require_role("user")
def get_allowed_models():
    org_id = str(request.args.get("org_id", "")).strip() or None
    group_id = str(request.args.get("group_id", "")).strip() or None
    models = _effective_models_for_current_user(org_id=org_id, group_id=group_id)
    return (
        jsonify({"models": [_serialize_model_definition(model) for model in models]}),
        200,
    )


@app.get("/models/enabled")
@require_role("user")
def get_enabled_models():
    org_id = str(request.args.get("org_id", "")).strip() or None
    group_id = str(request.args.get("group_id", "")).strip() or None
    models = _effective_models_for_current_user(org_id=org_id, group_id=group_id)
    normalized = [
        {
            "id": str(model.get("model_id", "")),
            "name": str((model.get("metadata") or {}).get("name") or model.get("model_id", "")),
            "provider": model.get("provider"),
            "description": str((model.get("metadata") or {}).get("description", "")) or None,
        }
        for model in models
    ]
    return jsonify({"models": normalized}), 200


@app.post("/llm/generate")
@require_role("user")
def generate_with_allowed_model():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    requested_model_id = str(payload.get("model_id", "")).strip()
    if not requested_model_id:
        return _json_error(400, "invalid_model_id", "model_id is required")

    org_id = str(payload.get("org_id", "")).strip() or None
    group_id = str(payload.get("group_id", "")).strip() or None
    prompt = str(payload.get("prompt", "")).strip()
    history = _coerce_chat_messages(payload.get("history", []))
    if prompt:
        history.append({"role": "user", "content": [{"type": "text", "text": prompt}]})

    if not history:
        return _json_error(400, "invalid_input", "history or prompt is required")

    max_tokens_raw = payload.get("max_tokens")
    max_tokens = int(max_tokens_raw) if isinstance(max_tokens_raw, int) and max_tokens_raw > 0 else None
    temperature_raw = payload.get("temperature")
    temperature = float(temperature_raw) if isinstance(temperature_raw, (int, float)) else None

    llm_response, status_code = _chat_completion_with_allowed_model(
        requested_model_id=requested_model_id,
        org_id=org_id,
        group_id=group_id,
        messages=history,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    if llm_response is None:
        return _json_error(502, "llm_unreachable", "LLM service unavailable")
    return jsonify(llm_response), status_code


@app.post("/inference")
@require_role("user")
def inference_endpoint():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    requested_model_id = str(payload.get("model", "")).strip()
    prompt = str(payload.get("prompt", "")).strip()
    if not requested_model_id:
        return _json_error(400, "invalid_model", "model is required")
    if not prompt:
        return _json_error(400, "invalid_prompt", "prompt is required")

    history = _coerce_chat_messages(payload.get("history", []))
    history.append({"role": "user", "content": [{"type": "text", "text": prompt}]})

    llm_response, status_code = _chat_completion_with_allowed_model(
        requested_model_id=requested_model_id,
        org_id=str(payload.get("org_id", "")).strip() or None,
        group_id=str(payload.get("group_id", "")).strip() or None,
        messages=history,
        max_tokens=None,
        temperature=None,
    )
    if llm_response is None:
        return _json_error(502, "llm_unreachable", "LLM service unavailable")
    if status_code >= 400:
        return jsonify(llm_response), status_code

    return (
        jsonify(
            {
                "output": _extract_output_text(llm_response),
                "response": llm_response,
            }
        ),
        200,
    )


@app.post("/v1/agent-executions")
@require_role("user")
def create_agent_execution():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    agent_id = str(payload.get("agent_id", "")).strip()
    execution_input = payload.get("input")
    if not agent_id:
        return _json_error(400, "invalid_agent_id", "agent_id is required")

    upstream_payload: dict[str, Any] = {
        "agent_id": agent_id,
        "input": execution_input if isinstance(execution_input, dict) else {},
        "requested_by_user_id": int(g.current_user["id"]),
        "runtime_profile": resolve_runtime_profile(_get_config().database_url),
    }
    for key in ("org_id", "group_id"):
        value = str(payload.get(key, "")).strip()
        if value:
            upstream_payload[key] = value

    agent_engine_url = os.getenv("AGENT_ENGINE_URL", "http://agent_engine:7000").rstrip("/")
    response_payload, status_code = _http_json_request(
        f"{agent_engine_url}/v1/agent-executions",
        upstream_payload,
    )
    if response_payload is None:
        return _json_error(502, "agent_engine_unreachable", "Agent engine unavailable")
    return jsonify(response_payload), status_code


@app.get("/v1/agent-executions/<execution_id>")
@require_role("user")
def get_agent_execution(execution_id: str):
    if not execution_id.strip():
        return _json_error(400, "invalid_execution_id", "execution_id is required")

    agent_engine_url = os.getenv("AGENT_ENGINE_URL", "http://agent_engine:7000").rstrip("/")
    response_payload, status_code = _http_get_json(
        f"{agent_engine_url}/v1/agent-executions/{execution_id.strip()}",
    )
    if response_payload is None:
        return _json_error(502, "agent_engine_unreachable", "Agent engine unavailable")
    return jsonify(response_payload), status_code


@app.post("/voice/wake-events")
def wake_events():
    payload = request.get_json(silent=True) or {}

    wake_word = str(payload.get("wake_word", "unknown")).strip() or "unknown"
    source_device_id = (
        str(payload.get("source_device_id", "default")).strip() or "default"
    )
    confidence = payload.get("confidence", 1.0)
    event_id = str(payload.get("event_id", "")).strip()

    try:
        confidence_value = float(confidence)
    except (TypeError, ValueError):
        return jsonify({"accepted": False, "reason": "invalid_confidence"}), 400

    detection_threshold = _get_float_env(
        "KWS_DETECTION_THRESHOLD", _DEFAULT_DETECTION_THRESHOLD
    )
    if confidence_value < detection_threshold:
        return jsonify({"accepted": False, "reason": "below_threshold"}), 202

    now = time.time()
    cooldown_ms = _get_int_env("KWS_COOLDOWN_MS", _DEFAULT_COOLDOWN_MS)
    cooldown_seconds = max(cooldown_ms, 0) / 1000.0

    if event_id:
        _trim_seen_event_ids(max_age_seconds=max(cooldown_seconds * 2.0, 5.0))
        if event_id in _seen_event_ids:
            return jsonify({"accepted": False, "reason": "duplicate_event_id"}), 202
        _seen_event_ids[event_id] = now

    dedupe_key = f"{source_device_id}:{wake_word}"
    last_seen = _last_wake_by_key.get(dedupe_key)
    if last_seen is not None and (now - last_seen) < cooldown_seconds:
        return jsonify({"accepted": False, "reason": "cooldown_active"}), 202

    _last_wake_by_key[dedupe_key] = now
    session_token = str(uuid4())

    response: dict[str, Any] = {
        "accepted": True,
        "wake_word": wake_word,
        "source_device_id": source_device_id,
        "confidence": confidence_value,
        "session_token": session_token,
        "received_at_unix": now,
    }
    if event_id:
        response["event_id"] = event_id

    return jsonify(response), 200


@app.get("/voice/health")
def voice_health():
    kws_url = os.getenv("KWS_URL", "http://kws:10400").rstrip("/")
    kws_health_url = f"{kws_url}/health"

    return (
        jsonify(
            {
                "status": "ok",
                "service": "backend",
                "voice": {
                    "kws": {"url": kws_url, "reachable": _http_json_ok(kws_health_url)},
                    "stt": {"configured": False},
                    "tts": {"configured": False},
                },
            }
        ),
        200,
    )


# Register modular v1 blueprints.
from .routes import agents as agents_routes
from .routes import auth as auth_routes
from .routes import models as models_routes
from .routes import registry as registry_routes
from .routes import runtime as runtime_routes
from .routes import system as system_routes
from .routes import tools as tools_routes

app.register_blueprint(auth_routes.bp)
app.register_blueprint(system_routes.bp)
app.register_blueprint(models_routes.bp)
app.register_blueprint(registry_routes.bp)
app.register_blueprint(agents_routes.bp)
app.register_blueprint(tools_routes.bp)
app.register_blueprint(runtime_routes.bp)
