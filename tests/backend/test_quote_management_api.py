from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.api.http import quotes as quotes_routes  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services.quote_management import QuoteListResult, QuoteRecord, QuoteSummary  # noqa: E402
from tests.backend.support.auth_harness import auth_header, login  # noqa: E402


@pytest.fixture()
def client(backend_test_client_factory, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store, config = backend_test_client_factory()
    monkeypatch.setattr(quotes_routes, "_database_url", lambda: config.database_url)
    yield test_client, user_store


def _auth(token: str) -> dict[str, str]:
    return auth_header(token)


def _login(client, identifier: str, password: str):
    return login(client, identifier, password)


def _create_user(user_store, *, username: str, role: str) -> dict[str, object]:
    return user_store.create_user(
        "ignored",
        email=f"{username}@example.com",
        username=username,
        password_hash=hash_password(f"{username}-pass-123"),
        role=role,
        is_active=True,
    )


def test_quote_management_routes_require_admin_role(client, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store = client
    standard = _create_user(user_store, username="user", role="user")
    admin = _create_user(user_store, username="admin", role="admin")

    user_token = _login(test_client, standard["username"], "user-pass-123").get_json()["access_token"]
    admin_token = _login(test_client, admin["username"], "admin-pass-123").get_json()["access_token"]

    monkeypatch.setattr(
        quotes_routes,
        "get_quote_summary",
        lambda _db: QuoteSummary(total=3, active=2, approved=1, by_language=[], by_tone=[], by_origin=[]),
    )

    forbidden = test_client.get("/v1/quotes/summary", headers=_auth(user_token))
    assert forbidden.status_code == 403

    allowed = test_client.get("/v1/quotes/summary", headers=_auth(admin_token))
    assert allowed.status_code == 200
    assert allowed.get_json()["summary"]["total"] == 3


def test_quote_management_list_returns_filters_and_pagination(client, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store = client
    admin = _create_user(user_store, username="admin", role="admin")
    token = _login(test_client, admin["username"], "admin-pass-123").get_json()["access_token"]

    now = datetime(2026, 3, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(
        quotes_routes,
        "list_quotes",
        lambda _db, *, filters, page, page_size: QuoteListResult(
            items=[QuoteRecord(
                id=11,
                language="en",
                text="Quote A",
                author="VANESSA",
                source_universe="Original",
                tone="reflective",
                tags=["ops"],
                is_active=True,
                is_approved=True,
                origin="local",
                external_ref=None,
                created_at=now,
                updated_at=now,
            )],
            total=1,
        ),
    )

    response = test_client.get(
        "/v1/quotes?page=2&page_size=5&tone=reflective&source_universe=Original",
        headers=_auth(token),
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "items": [{
            "id": 11,
            "language": "en",
            "text": "Quote A",
            "author": "VANESSA",
            "source_universe": "Original",
            "tone": "reflective",
            "tags": ["ops"],
            "is_active": True,
            "is_approved": True,
            "origin": "local",
            "external_ref": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }],
        "page": 2,
        "page_size": 5,
        "total": 1,
        "filters": {
            "source_universe": "Original",
            "tone": "reflective",
        },
    }


def test_quote_management_can_create_and_update_quotes(client, monkeypatch: pytest.MonkeyPatch):
    test_client, user_store = client
    admin = _create_user(user_store, username="admin", role="admin")
    token = _login(test_client, admin["username"], "admin-pass-123").get_json()["access_token"]

    now = datetime(2026, 3, 12, tzinfo=timezone.utc)
    created_row = QuoteRecord(
        id=17,
        language="en",
        text="Fresh quote",
        author="Curator",
        source_universe="Original",
        tone="funny",
        tags=["funny"],
        is_active=True,
        is_approved=True,
        origin="local",
        external_ref=None,
        created_at=now,
        updated_at=now,
    )
    updated_row = QuoteRecord(
        id=17,
        language="en",
        text="Updated quote",
        author="Curator",
        source_universe="Original",
        tone="funny",
        tags=["funny"],
        is_active=True,
        is_approved=True,
        origin="local",
        external_ref=None,
        created_at=now,
        updated_at=now,
    )
    monkeypatch.setattr(quotes_routes, "create_quote", lambda _db, *, payload: created_row)
    monkeypatch.setattr(quotes_routes, "update_quote", lambda _db, *, quote_id, payload: updated_row)

    payload = {
        "language": "en",
        "text": "Fresh quote",
        "author": "Curator",
        "source_universe": "Original",
        "tone": "funny",
        "tags": ["funny"],
        "is_active": True,
        "is_approved": True,
        "origin": "local",
        "external_ref": "",
    }

    created = test_client.post("/v1/quotes", headers=_auth(token), json=payload)
    assert created.status_code == 201
    assert created.get_json()["quote"]["id"] == 17

    updated = test_client.put("/v1/quotes/17", headers=_auth(token), json={**payload, "text": "Updated quote"})
    assert updated.status_code == 200
    assert updated.get_json()["quote"]["text"] == "Updated quote"
