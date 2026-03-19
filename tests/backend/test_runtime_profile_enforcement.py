from __future__ import annotations

import pytest

from app.routes import model_catalog_v1 as model_catalog_routes  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services.connectivity_policy import ConnectivityPolicyError, assert_internet_allowed  # noqa: E402
from app.services.hf_discovery import discover_hf_models, get_hf_model_details  # noqa: E402
from app.services.model_downloader import download_from_huggingface  # noqa: E402
from tests.backend.support.auth_harness import auth_header, login  # noqa: E402


@pytest.fixture()
def client(backend_test_client_factory, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("VANESSA_RUNTIME_PROFILE", raising=False)
    monkeypatch.delenv("VANESSA_RUNTIME_PROFILE_FORCE", raising=False)
    test_client, user_store, config = backend_test_client_factory()
    monkeypatch.setattr(model_catalog_routes, "_config", lambda: config)
    monkeypatch.setattr(model_catalog_routes, "discover_hf_models", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("should not call")))
    monkeypatch.setattr(model_catalog_routes, "get_hf_model_details", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("should not call")))
    yield test_client, user_store, config


def _auth(token: str) -> dict[str, str]:
    return auth_header(token)


def _login(client, identifier: str, password: str):
    return login(client, identifier, password)


def test_internet_features_are_consistently_blocked_in_offline_profile(client):
    test_client, user_store, config = client
    root = user_store.create_user(
        "ignored",
        email="root@example.com",
        username="root",
        password_hash=hash_password("root-pass-123"),
        role="superadmin",
        is_active=True,
    )
    token = _login(test_client, root["username"], "root-pass-123").get_json()["access_token"]

    for method, path, expected_message in [
        ("get", "/v1/models/discovery/huggingface?query=llama", "Model discovery disabled for runtime profile 'offline'"),
        ("get", "/v1/models/discovery/huggingface/meta-llama/Llama-3-8B-Instruct", "Model discovery disabled for runtime profile 'offline'"),
        ("post", "/v1/models/downloads", "Model download disabled for runtime profile 'offline'"),
    ]:
        response = getattr(test_client, method)(
            path,
            headers=_auth(token),
            json={"source_id": "meta-llama/Llama-3-8B-Instruct"} if method == "post" else None,
        )
        assert response.status_code == 403
        assert response.get_json() == {
            "error": "runtime_profile_blocks_internet",
            "message": expected_message,
        }

    for operation in ["Model discovery", "Model download", "Web search"]:
        with pytest.raises(ConnectivityPolicyError) as exc_info:
            assert_internet_allowed(config.database_url, operation)
        assert exc_info.value.code == "runtime_profile_blocks_internet"
        assert str(exc_info.value) == f"{operation} disabled for runtime profile 'offline'"


def test_outbound_services_share_same_runtime_policy_denial(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("VANESSA_RUNTIME_PROFILE", raising=False)
    monkeypatch.delenv("VANESSA_RUNTIME_PROFILE_FORCE", raising=False)

    for call in [
        lambda: discover_hf_models(database_url="postgresql://example", query="llama"),
        lambda: get_hf_model_details("meta-llama/Llama-3-8B-Instruct", database_url="postgresql://example"),
        lambda: download_from_huggingface(
            database_url="postgresql://example",
            source_id="meta-llama/Llama-3-8B-Instruct",
            storage_root="/tmp/models",
            token=None,
        ),
    ]:
        with pytest.raises(ConnectivityPolicyError) as exc_info:
            call()
        assert exc_info.value.code == "runtime_profile_blocks_internet"
        assert exc_info.value.status_code == 403
