from __future__ import annotations

from flask import Blueprint

from ..authz import require_auth, require_role

bp = Blueprint("legacy_auth", __name__)


def _m():
    import app.app as backend_app_module

    return backend_app_module


@bp.post("/auth/register")
def register_user():
    return _m().register_user()


@bp.post("/auth/login")
def login_user():
    return _m().login_user()


@bp.post("/auth/logout")
@require_auth
def logout_user():
    return _m().logout_user()


@bp.get("/auth/me")
@require_auth
def auth_me():
    return _m().auth_me()


@bp.post("/auth/users/<int:user_id>/activate")
@require_role("admin")
def activate_pending_user(user_id: int):
    return _m().activate_pending_user(user_id)


@bp.get("/auth/users")
@require_role("admin")
def auth_users_list():
    return _m().auth_users_list()


@bp.patch("/auth/users/<int:user_id>/role")
@require_role("superadmin")
def update_role(user_id: int):
    return _m().update_role(user_id)


@bp.get("/admin/ping")
@require_role("admin")
def admin_ping():
    return _m().admin_ping()


@bp.get("/superadmin/ping")
@require_role("superadmin")
def superadmin_ping():
    return _m().superadmin_ping()
