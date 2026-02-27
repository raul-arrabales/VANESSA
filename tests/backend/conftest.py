from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app.app as backend_app_module  # noqa: E402
from app.app import app  # noqa: E402
from app.config import AuthConfig  # noqa: E402
from app.handlers import auth_handlers as auth_handler  # noqa: E402
from tests.backend.support.auth_harness import InMemoryUserStore, build_test_auth_config, patch_auth_bootstrap  # noqa: E402


@pytest.fixture()
def backend_test_client_factory(monkeypatch: pytest.MonkeyPatch):
    def _factory(
        *,
        config_overrides: dict | None = None,
        extra_setup=None,
    ):
        user_store = InMemoryUserStore(users={})
        config = build_test_auth_config(AuthConfig, **(config_overrides or {}))
        patch_auth_bootstrap(
            monkeypatch,
            config=config,
            user_store=user_store,
            backend_app_module=backend_app_module,
            auth_handler_module=auth_handler,
        )
        if callable(extra_setup):
            extra_setup(monkeypatch, config, user_store)

        app.config.update(TESTING=True)
        test_client = app.test_client()
        return test_client, user_store, config

    return _factory

