from __future__ import annotations

from typing import Any

import pytest

from app.routes import policy as policy_routes  # noqa: E402
from app.security import hash_password  # noqa: E402
from tests.backend.support.auth_harness import auth_header, login  # noqa: E402


@pytest.fixture()
def client(backend_test_client_factory, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store, config = backend_test_client_factory()
    rules: list[dict[str, Any]] = []
    monkeypatch.setattr(
        policy_routes,
        "create_policy_rule",
        lambda _db, **kwargs: (rules.append({"id": len(rules) + 1, **kwargs}) or rules[-1]),
    )
    monkeypatch.setattr(policy_routes, "list_policy_rules", lambda _db, scope_type=None, scope_id=None: rules)
    monkeypatch.setattr(policy_routes, "get_auth_config", lambda: config)
    yield test_client, user_store


def _auth(token: str) -> dict[str, str]:
    return auth_header(token)


def _login(client, identifier: str, password: str):
    return login(client, identifier, password)


def test_superadmin_can_create_and_list_policy_rules(client):
    test_client, users = client
    root = users.create_user(
        "ignored",
        email="root@example.com",
        username="root",
        password_hash=hash_password("root-pass-123"),
        role="superadmin",
        is_active=True,
    )
    token = _login(test_client, root["username"], "root-pass-123").get_json()["access_token"]

    created = test_client.post(
        "/v1/policy/rules",
        headers=_auth(token),
        json={
            "scope_type": "user",
            "scope_id": "5",
            "resource_type": "entity",
            "resource_id": "agent.alpha",
            "effect": "deny",
            "rule": {"action": "execute"},
        },
    )
    assert created.status_code == 201

    listed = test_client.get("/v1/policy/rules", headers=_auth(token))
    assert listed.status_code == 200
    assert listed.get_json()["rules"][0]["resource_id"] == "agent.alpha"
