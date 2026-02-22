from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import g, jsonify

Role = str
AUTH_ROLES = {"superadmin", "admin", "user"}
_ROLE_ORDER = {"user": 1, "admin": 2, "superadmin": 3}


def _error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


def require_auth(view: Callable):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if getattr(g, "current_user", None) is None:
            reason = getattr(g, "auth_error", "missing_auth")
            return _error(401, reason, "Authentication required")
        return view(*args, **kwargs)

    return wrapped


def require_role(required_role: Role):
    def decorator(view: Callable):
        @wraps(view)
        @require_auth
        def wrapped(*args, **kwargs):
            current_role = str(g.current_user.get("role", "user"))
            if _ROLE_ORDER.get(current_role, 0) < _ROLE_ORDER.get(required_role, 0):
                return _error(403, "insufficient_role", "Insufficient role")
            return view(*args, **kwargs)

        return wrapped

    return decorator
