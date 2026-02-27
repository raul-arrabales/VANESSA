from __future__ import annotations

from flask import g, jsonify, request

from ..authz import AUTH_ROLES
from ..repositories.users import (
    activate_user,
    count_users_by_role,
    create_user,
    find_user_by_id,
    find_user_by_identifier,
    list_users,
    sanitize_user_record,
    update_user_role,
)
from ..security import hash_password, verify_password
from ..services.auth_runtime import auth_ready_or_503, get_config
from ..auth_tokens import issue_access_token

_MIN_PASSWORD_LENGTH = 8


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


def _validate_password_strength(password: str):
    if len(password) < _MIN_PASSWORD_LENGTH:
        return _json_error(
            422,
            "weak_password",
            f"Password must be at least {_MIN_PASSWORD_LENGTH} characters",
        )
    return None


def _extract_register_actor() -> dict[str, object] | None:
    actor = getattr(g, "current_user", None)
    if actor is None:
        return None
    return actor


def register_user():
    if (ready_error := auth_ready_or_503(_json_error)) is not None:
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
        if not get_config().allow_self_register:
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
            get_config().database_url,
            email=email,
            username=username,
            password_hash=hash_password(password),
            role=role,
            is_active=is_active,
        )
    except ValueError:
        return _json_error(409, "duplicate_user", "Email or username already exists")

    return jsonify({"user": sanitize_user_record(created)}), 201


def login_user():
    if (ready_error := auth_ready_or_503(_json_error)) is not None:
        return ready_error

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    identifier = str(payload.get("identifier") or payload.get("email") or payload.get("username") or "").strip()
    password = str(payload.get("password", ""))

    if not identifier or not password:
        return _json_error(400, "missing_credentials", "Identifier and password are required")

    user = find_user_by_identifier(get_config().database_url, identifier)
    if user is None:
        return _json_error(401, "invalid_credentials", "Invalid credentials")

    if not verify_password(password, str(user.get("password_hash", ""))):
        return _json_error(401, "invalid_credentials", "Invalid credentials")

    if not bool(user.get("is_active", False)):
        return _json_error(403, "account_inactive", "Account pending activation")

    token = issue_access_token(user, get_config())
    return (
        jsonify(
            {
                "access_token": token,
                "token_type": "bearer",
                "expires_in": get_config().access_token_ttl_seconds,
                "user": sanitize_user_record(user),
            }
        ),
        200,
    )


def logout_user():
    return jsonify({"logged_out": True}), 200


def auth_me():
    return jsonify({"user": sanitize_user_record(g.current_user)}), 200


def activate_pending_user(user_id: int):
    if (ready_error := auth_ready_or_503(_json_error)) is not None:
        return ready_error

    target_user = find_user_by_id(get_config().database_url, user_id)
    if target_user is None:
        return _json_error(404, "user_not_found", "User not found")

    actor_role = str(g.current_user.get("role", "user"))
    target_role = str(target_user.get("role", "user"))

    if actor_role == "admin" and target_role != "user":
        return _json_error(403, "insufficient_role", "Admin cannot activate elevated roles")

    updated = activate_user(get_config().database_url, user_id)
    if updated is None:
        return _json_error(404, "user_not_found", "User not found")

    return jsonify({"user": sanitize_user_record(updated)}), 200


def auth_users_list():
    if (ready_error := auth_ready_or_503(_json_error)) is not None:
        return ready_error

    status = str(request.args.get("status", "")).strip().lower()
    if status and status not in {"pending", "active"}:
        return _json_error(400, "invalid_status", "status must be one of: pending, active")

    if status == "pending":
        active_filter = False
    elif status == "active":
        active_filter = True
    else:
        active_filter = None

    users = [sanitize_user_record(user) for user in list_users(get_config().database_url, is_active=active_filter)]
    return jsonify({"users": users}), 200


def update_role(user_id: int):
    if (ready_error := auth_ready_or_503(_json_error)) is not None:
        return ready_error

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    requested_role = str(payload.get("role", "")).strip().lower()
    if requested_role not in AUTH_ROLES:
        return _json_error(400, "invalid_role", "Invalid role value")

    target_user = find_user_by_id(get_config().database_url, user_id)
    if target_user is None:
        return _json_error(404, "user_not_found", "User not found")

    target_role = str(target_user.get("role", "user"))
    if target_role == "superadmin" and requested_role != "superadmin":
        superadmin_count = count_users_by_role(get_config().database_url, "superadmin")
        if superadmin_count <= 1:
            return _json_error(
                409,
                "last_superadmin_demote_forbidden",
                "Cannot demote the last remaining superadmin",
            )

    updated_user = update_user_role(get_config().database_url, user_id, requested_role)
    if updated_user is None:
        return _json_error(404, "user_not_found", "User not found")

    return jsonify({"user": sanitize_user_record(updated_user)}), 200


def admin_ping():
    return jsonify({"status": "ok", "scope": "admin"}), 200


def superadmin_ping():
    return jsonify({"status": "ok", "scope": "superadmin"}), 200
