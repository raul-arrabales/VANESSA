from __future__ import annotations

import pytest

from tests.backend.support.auth_harness import auth_header, login
from app.security import hash_password  # noqa: E402

@pytest.fixture()
def client(backend_test_client_factory):
    test_client, user_store, _config = backend_test_client_factory()
    yield test_client, user_store


def test_self_registration_creates_inactive_user(client):
    test_client, _ = client
    response = test_client.post(
        "/auth/register",
        json={"email": "u1@example.com", "username": "u1", "password": "password123"},
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["user"]["role"] == "user"
    assert payload["user"]["is_active"] is False


def test_non_superadmin_cannot_assign_elevated_role(client):
    test_client, _ = client
    response = test_client.post(
        "/auth/register",
        json={
            "email": "u2@example.com",
            "username": "u2",
            "password": "password123",
            "role": "admin",
        },
    )

    assert response.status_code == 403


def test_superadmin_can_create_elevated_roles(client):
    test_client, store = client
    superadmin = store.create_user(
        "ignored",
        email="root@example.com",
        username="root",
        password_hash=hash_password("root-pass-123"),
        role="superadmin",
        is_active=True,
    )

    token = login(test_client, "root", "root-pass-123").get_json()["access_token"]
    response = test_client.post(
        "/auth/register",
        headers=auth_header(token),
        json={
            "email": "admin@example.com",
            "username": "admin1",
            "password": "password123",
            "role": "admin",
            "is_active": True,
        },
    )

    assert superadmin["role"] == "superadmin"
    assert response.status_code == 201
    assert response.get_json()["user"]["role"] == "admin"


def test_login_success_and_wrong_password(client):
    test_client, store = client
    store.create_user(
        "ignored",
        email="active@example.com",
        username="active",
        password_hash=hash_password("good-pass-123"),
        role="user",
        is_active=True,
    )

    success = login(test_client, "active", "good-pass-123")
    assert success.status_code == 200
    assert success.get_json()["token_type"] == "bearer"

    bad = login(test_client, "active", "wrong-password")
    assert bad.status_code == 401


def test_inactive_user_login_rejected(client):
    test_client, store = client
    store.create_user(
        "ignored",
        email="inactive@example.com",
        username="inactive",
        password_hash=hash_password("inactive-pass"),
        role="user",
        is_active=False,
    )

    response = login(test_client, "inactive", "inactive-pass")
    assert response.status_code == 403


def test_auth_required_endpoint_rejects_without_token(client):
    test_client, _ = client
    response = test_client.get("/auth/me")
    assert response.status_code == 401


def test_insufficient_role_rejected_on_superadmin_route(client):
    test_client, store = client
    store.create_user(
        "ignored",
        email="admin@example.com",
        username="admin",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )
    token = login(test_client, "admin", "admin-pass-123").get_json()["access_token"]

    response = test_client.get("/superadmin/ping", headers=auth_header(token))
    assert response.status_code == 403


def test_correct_role_allowed_on_protected_route(client):
    test_client, store = client
    store.create_user(
        "ignored",
        email="adminok@example.com",
        username="adminok",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )
    token = login(test_client, "adminok", "admin-pass-123").get_json()["access_token"]

    response = test_client.get("/admin/ping", headers=auth_header(token))
    assert response.status_code == 200


def test_activation_policy_for_admin_and_superadmin(client):
    test_client, store = client
    admin = store.create_user(
        "ignored",
        email="admina@example.com",
        username="admina",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )
    superadmin = store.create_user(
        "ignored",
        email="super@example.com",
        username="super",
        password_hash=hash_password("super-pass-123"),
        role="superadmin",
        is_active=True,
    )
    pending_user = store.create_user(
        "ignored",
        email="pending-user@example.com",
        username="pendinguser",
        password_hash=hash_password("pending-pass-123"),
        role="user",
        is_active=False,
    )
    pending_admin = store.create_user(
        "ignored",
        email="pending-admin@example.com",
        username="pendingadmin",
        password_hash=hash_password("pending-pass-123"),
        role="admin",
        is_active=False,
    )

    admin_token = login(test_client, admin["username"], "admin-pass-123").get_json()["access_token"]
    super_token = login(test_client, superadmin["username"], "super-pass-123").get_json()["access_token"]

    can_activate_user = test_client.post(
        f"/auth/users/{pending_user['id']}/activate",
        headers=auth_header(admin_token),
    )
    assert can_activate_user.status_code == 200
    assert can_activate_user.get_json()["user"]["is_active"] is True

    cannot_activate_admin = test_client.post(
        f"/auth/users/{pending_admin['id']}/activate",
        headers=auth_header(admin_token),
    )
    assert cannot_activate_admin.status_code == 403

    superadmin_can_activate_admin = test_client.post(
        f"/auth/users/{pending_admin['id']}/activate",
        headers=auth_header(super_token),
    )
    assert superadmin_can_activate_admin.status_code == 200
    assert superadmin_can_activate_admin.get_json()["user"]["is_active"] is True


def test_list_pending_users_for_admin(client):
    test_client, store = client
    admin = store.create_user(
        "ignored",
        email="adminlist@example.com",
        username="adminlist",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )
    store.create_user(
        "ignored",
        email="pending-list@example.com",
        username="pendinglist",
        password_hash=hash_password("pending-pass-123"),
        role="user",
        is_active=False,
    )
    store.create_user(
        "ignored",
        email="active-list@example.com",
        username="activelist",
        password_hash=hash_password("active-pass-123"),
        role="user",
        is_active=True,
    )

    admin_token = login(test_client, admin["username"], "admin-pass-123").get_json()["access_token"]
    response = test_client.get("/auth/users?status=pending", headers=auth_header(admin_token))

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["users"]) == 1
    assert payload["users"][0]["username"] == "pendinglist"
    assert payload["users"][0]["is_active"] is False


def test_superadmin_can_promote_user_to_admin(client):
    test_client, store = client
    superadmin = store.create_user(
        "ignored",
        email="rootset@example.com",
        username="rootset",
        password_hash=hash_password("super-pass-123"),
        role="superadmin",
        is_active=True,
    )
    pending_user = store.create_user(
        "ignored",
        email="promote@example.com",
        username="promote",
        password_hash=hash_password("pending-pass-123"),
        role="user",
        is_active=False,
    )

    super_token = login(test_client, superadmin["username"], "super-pass-123").get_json()["access_token"]
    response = test_client.patch(
        f"/auth/users/{pending_user['id']}/role",
        headers=auth_header(super_token),
        json={"role": "admin"},
    )

    assert response.status_code == 200
    assert response.get_json()["user"]["role"] == "admin"
    assert response.get_json()["user"]["is_active"] is False


def test_admin_cannot_update_roles(client):
    test_client, store = client
    admin = store.create_user(
        "ignored",
        email="noroleadmin@example.com",
        username="noroleadmin",
        password_hash=hash_password("admin-pass-123"),
        role="admin",
        is_active=True,
    )
    target = store.create_user(
        "ignored",
        email="target@example.com",
        username="target",
        password_hash=hash_password("target-pass-123"),
        role="user",
        is_active=True,
    )

    admin_token = login(test_client, admin["username"], "admin-pass-123").get_json()["access_token"]
    response = test_client.patch(
        f"/auth/users/{target['id']}/role",
        headers=auth_header(admin_token),
        json={"role": "admin"},
    )
    assert response.status_code == 403


def test_last_superadmin_cannot_demote_self(client):
    test_client, store = client
    superadmin = store.create_user(
        "ignored",
        email="lonely-root@example.com",
        username="lonelyroot",
        password_hash=hash_password("super-pass-123"),
        role="superadmin",
        is_active=True,
    )

    super_token = login(test_client, superadmin["username"], "super-pass-123").get_json()["access_token"]
    response = test_client.patch(
        f"/auth/users/{superadmin['id']}/role",
        headers=auth_header(super_token),
        json={"role": "admin"},
    )

    assert response.status_code == 409
    assert response.get_json()["error"] == "last_superadmin_demote_forbidden"
