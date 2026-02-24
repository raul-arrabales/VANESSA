from __future__ import annotations

import os
import time
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from flask import Flask, g, jsonify, request

from .auth_tokens import TOKEN_PREFIX, decode_access_token, issue_access_token
from .authz import AUTH_ROLES, require_auth, require_role
from .config import AuthConfig, get_auth_config
from .db import run_auth_schema_migration
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


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


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
    stale_ids = [event_id for event_id, seen_ts in _seen_event_ids.items() if seen_ts < cutoff]
    for event_id in stale_ids:
        _seen_event_ids.pop(event_id, None)


def _http_json_ok(url: str) -> bool:
    req = Request(url, method="GET")
    try:
        with urlopen(req, timeout=_DEFAULT_HTTP_TIMEOUT_SECONDS) as response:
            return 200 <= response.status < 300
    except URLError:
        return False


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
        print("[WARN] Incomplete superadmin bootstrap env vars; skipping bootstrap user creation.")
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

    token = auth_header[len(prefix):].strip()
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
    requested_role = str(requested_role_raw).strip().lower() if requested_role_raw is not None else ""
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
            return _json_error(403, "self_registration_disabled", "Self registration is disabled")
        if requested_role and requested_role != "user":
            return _json_error(403, "role_assignment_forbidden", "Only superadmin can set custom role")
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
                return _json_error(403, "role_assignment_forbidden", "Admin can only create user role")
            role = "user"
            is_active = False
        else:
            return _json_error(403, "insufficient_role", "Only admin or superadmin can create users")

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

    identifier = str(payload.get("identifier") or payload.get("email") or payload.get("username") or "").strip()
    password = str(payload.get("password", ""))

    if not identifier or not password:
        return _json_error(400, "missing_credentials", "Identifier and password are required")

    user = find_user_by_identifier(_get_config().database_url, identifier)
    if user is None:
        return _json_error(401, "invalid_credentials", "Invalid credentials")

    if not verify_password(password, str(user.get("password_hash", ""))):
        return _json_error(401, "invalid_credentials", "Invalid credentials")

    if not bool(user.get("is_active", False)):
        return _json_error(403, "account_inactive", "Account pending activation")

    token = issue_access_token(user, _get_config())
    return jsonify(
        {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": _get_config().access_token_ttl_seconds,
            "user": sanitize_user_record(user),
        }
    ), 200


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
        return _json_error(403, "insufficient_role", "Admin cannot activate elevated roles")

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
        return _json_error(400, "invalid_status", "status must be one of: pending, active")

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


@app.post("/voice/wake-events")
def wake_events():
    payload = request.get_json(silent=True) or {}

    wake_word = str(payload.get("wake_word", "unknown")).strip() or "unknown"
    source_device_id = str(payload.get("source_device_id", "default")).strip() or "default"
    confidence = payload.get("confidence", 1.0)
    event_id = str(payload.get("event_id", "")).strip()

    try:
        confidence_value = float(confidence)
    except (TypeError, ValueError):
        return jsonify({"accepted": False, "reason": "invalid_confidence"}), 400

    detection_threshold = _get_float_env("KWS_DETECTION_THRESHOLD", _DEFAULT_DETECTION_THRESHOLD)
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

    return jsonify(
        {
            "status": "ok",
            "service": "backend",
            "voice": {
                "kws": {"url": kws_url, "reachable": _http_json_ok(kws_health_url)},
                "stt": {"configured": False},
                "tts": {"configured": False},
            },
        }
    ), 200
