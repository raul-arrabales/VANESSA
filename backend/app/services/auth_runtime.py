from __future__ import annotations

from flask import current_app

from ..config import AuthConfig, get_auth_config
from ..db import run_auth_schema_migration
from ..repositories.users import count_users, create_user
from ..security import hash_password
from . import auth_lifecycle
from .knowledge_chat_bootstrap import ensure_knowledge_chat_agent
from .model_download_worker import ensure_download_worker_started
from .runtime_profile_service import seed_runtime_profile_from_config
from .tool_registry_bootstrap import ensure_builtin_tools

_knowledge_chat_bootstrapped = False
_builtin_tools_bootstrapped = False


def get_config() -> AuthConfig:
    return auth_lifecycle.get_config(get_auth_config)


def bootstrap_superadmin(config: AuthConfig) -> None:
    auth_lifecycle.bootstrap_superadmin(
        config,
        count_users_fn=count_users,
        create_user_fn=create_user,
        hash_password_fn=hash_password,
    )


def ensure_auth_initialized() -> bool:
    global _knowledge_chat_bootstrapped, _builtin_tools_bootstrapped

    ready = auth_lifecycle.ensure_auth_initialized(
        app_logger=current_app.logger,
        get_config_fn=get_config,
        run_auth_schema_migration_fn=run_auth_schema_migration,
        bootstrap_superadmin_fn=bootstrap_superadmin,
        ensure_download_worker_started_fn=ensure_download_worker_started,
    )
    if not ready:
        return False
    seed_runtime_profile_from_config(get_config().database_url)
    if not _knowledge_chat_bootstrapped:
        try:
            _knowledge_chat_bootstrapped = ensure_knowledge_chat_agent(get_config().database_url)
        except Exception as exc:  # pragma: no cover - guarded by route behavior tests
            current_app.logger.warning("Knowledge chat bootstrap unavailable: %s", exc)
    if not _builtin_tools_bootstrapped:
        try:
            _builtin_tools_bootstrapped = ensure_builtin_tools(get_config().database_url)
        except Exception as exc:  # pragma: no cover - guarded by route behavior tests
            current_app.logger.warning("Builtin tool bootstrap unavailable: %s", exc)
    return True


def auth_ready_or_503(json_error_fn):
    return auth_lifecycle.auth_ready_or_503(
        ensure_auth_initialized_fn=ensure_auth_initialized,
        json_error_fn=json_error_fn,
    )
