from __future__ import annotations


def _m():
    import app.app as backend_app_module

    return backend_app_module


def register_user():
    m = _m()
    if (ready_error := m._auth_ready_or_503()) is not None:
        return ready_error

    payload = m.request.get_json(silent=True)
    if not isinstance(payload, dict):
        return m._json_error(400, "invalid_payload", "Expected JSON object")

    email = str(payload.get("email", "")).strip().lower()
    username = str(payload.get("username", "")).strip().lower()
    password = str(payload.get("password", ""))
    requested_role_raw = payload.get("role")
    requested_role = str(requested_role_raw).strip().lower() if requested_role_raw is not None else ""
    requested_is_active = payload.get("is_active")

    if not email or "@" not in email:
        return m._json_error(400, "invalid_email", "A valid email is required")
    if not username:
        return m._json_error(400, "invalid_username", "Username is required")
    if not password:
        return m._json_error(400, "invalid_password", "Password is required")

    if (password_error := m._validate_password_strength(password)) is not None:
        return password_error

    actor = m._extract_register_actor()
    role = "user"
    is_active = False

    if actor is None:
        if not m._get_config().allow_self_register:
            return m._json_error(403, "self_registration_disabled", "Self registration is disabled")
        if requested_role and requested_role != "user":
            return m._json_error(403, "role_assignment_forbidden", "Only superadmin can set custom role")
        role = "user"
        is_active = False
    else:
        actor_role = str(actor.get("role", "user"))
        if actor_role == "superadmin":
            if requested_role and requested_role not in m.AUTH_ROLES:
                return m._json_error(400, "invalid_role", "Invalid role value")
            role = requested_role or "user"
            if requested_is_active is None:
                is_active = role in {"admin", "superadmin"}
            else:
                is_active = bool(requested_is_active)
        elif actor_role == "admin":
            if requested_role and requested_role != "user":
                return m._json_error(403, "role_assignment_forbidden", "Admin can only create user role")
            role = "user"
            is_active = False
        else:
            return m._json_error(403, "insufficient_role", "Only admin or superadmin can create users")

    try:
        created = m.create_user(
            m._get_config().database_url,
            email=email,
            username=username,
            password_hash=m.hash_password(password),
            role=role,
            is_active=is_active,
        )
    except ValueError:
        return m._json_error(409, "duplicate_user", "Email or username already exists")

    return m.jsonify({"user": m.sanitize_user_record(created)}), 201


def login_user():
    m = _m()
    if (ready_error := m._auth_ready_or_503()) is not None:
        return ready_error

    payload = m.request.get_json(silent=True)
    if not isinstance(payload, dict):
        return m._json_error(400, "invalid_payload", "Expected JSON object")

    identifier = str(payload.get("identifier") or payload.get("email") or payload.get("username") or "").strip()
    password = str(payload.get("password", ""))

    if not identifier or not password:
        return m._json_error(400, "missing_credentials", "Identifier and password are required")

    user = m.find_user_by_identifier(m._get_config().database_url, identifier)
    if user is None:
        return m._json_error(401, "invalid_credentials", "Invalid credentials")

    if not m.verify_password(password, str(user.get("password_hash", ""))):
        return m._json_error(401, "invalid_credentials", "Invalid credentials")

    if not bool(user.get("is_active", False)):
        return m._json_error(403, "account_inactive", "Account pending activation")

    token = m.issue_access_token(user, m._get_config())
    return (
        m.jsonify(
            {
                "access_token": token,
                "token_type": "bearer",
                "expires_in": m._get_config().access_token_ttl_seconds,
                "user": m.sanitize_user_record(user),
            }
        ),
        200,
    )


def logout_user():
    m = _m()
    return m.jsonify({"logged_out": True}), 200


def auth_me():
    m = _m()
    return m.jsonify({"user": m.sanitize_user_record(m.g.current_user)}), 200


def activate_pending_user(user_id: int):
    m = _m()
    if (ready_error := m._auth_ready_or_503()) is not None:
        return ready_error

    target_user = m.find_user_by_id(m._get_config().database_url, user_id)
    if target_user is None:
        return m._json_error(404, "user_not_found", "User not found")

    actor_role = str(m.g.current_user.get("role", "user"))
    target_role = str(target_user.get("role", "user"))

    if actor_role == "admin" and target_role != "user":
        return m._json_error(403, "insufficient_role", "Admin cannot activate elevated roles")

    updated = m.activate_user(m._get_config().database_url, user_id)
    if updated is None:
        return m._json_error(404, "user_not_found", "User not found")

    return m.jsonify({"user": m.sanitize_user_record(updated)}), 200


def auth_users_list():
    m = _m()
    if (ready_error := m._auth_ready_or_503()) is not None:
        return ready_error

    status = str(m.request.args.get("status", "")).strip().lower()
    if status and status not in {"pending", "active"}:
        return m._json_error(400, "invalid_status", "status must be one of: pending, active")

    if status == "pending":
        active_filter = False
    elif status == "active":
        active_filter = True
    else:
        active_filter = None

    users = [m.sanitize_user_record(user) for user in m.list_users(m._get_config().database_url, is_active=active_filter)]
    return m.jsonify({"users": users}), 200


def update_role(user_id: int):
    m = _m()
    if (ready_error := m._auth_ready_or_503()) is not None:
        return ready_error

    payload = m.request.get_json(silent=True)
    if not isinstance(payload, dict):
        return m._json_error(400, "invalid_payload", "Expected JSON object")

    requested_role = str(payload.get("role", "")).strip().lower()
    if requested_role not in m.AUTH_ROLES:
        return m._json_error(400, "invalid_role", "Invalid role value")

    target_user = m.find_user_by_id(m._get_config().database_url, user_id)
    if target_user is None:
        return m._json_error(404, "user_not_found", "User not found")

    target_role = str(target_user.get("role", "user"))
    if target_role == "superadmin" and requested_role != "superadmin":
        superadmin_count = m.count_users_by_role(m._get_config().database_url, "superadmin")
        if superadmin_count <= 1:
            return m._json_error(
                409,
                "last_superadmin_demote_forbidden",
                "Cannot demote the last remaining superadmin",
            )

    updated_user = m.update_user_role(m._get_config().database_url, user_id, requested_role)
    if updated_user is None:
        return m._json_error(404, "user_not_found", "User not found")

    return m.jsonify({"user": m.sanitize_user_record(updated_user)}), 200


def admin_ping():
    m = _m()
    return m.jsonify({"status": "ok", "scope": "admin"}), 200


def superadmin_ping():
    m = _m()
    return m.jsonify({"status": "ok", "scope": "superadmin"}), 200
