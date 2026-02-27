from __future__ import annotations

from flask import Blueprint

from ..authz import require_auth, require_role
from ..handlers import legacy_auth

bp = Blueprint("legacy_auth", __name__)


@bp.post("/auth/register")
def register_user():
    return legacy_auth.register_user()


@bp.post("/auth/login")
def login_user():
    return legacy_auth.login_user()


@bp.post("/auth/logout")
@require_auth
def logout_user():
    return legacy_auth.logout_user()


@bp.get("/auth/me")
@require_auth
def auth_me():
    return legacy_auth.auth_me()


@bp.post("/auth/users/<int:user_id>/activate")
@require_role("admin")
def activate_pending_user(user_id: int):
    return legacy_auth.activate_pending_user(user_id)


@bp.get("/auth/users")
@require_role("admin")
def auth_users_list():
    return legacy_auth.auth_users_list()


@bp.patch("/auth/users/<int:user_id>/role")
@require_role("superadmin")
def update_role(user_id: int):
    return legacy_auth.update_role(user_id)


@bp.get("/admin/ping")
@require_role("admin")
def admin_ping():
    return legacy_auth.admin_ping()


@bp.get("/superadmin/ping")
@require_role("superadmin")
def superadmin_ping():
    return legacy_auth.superadmin_ping()
