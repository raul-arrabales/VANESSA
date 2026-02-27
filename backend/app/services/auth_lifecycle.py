from __future__ import annotations

from app.config import AuthConfig

_auth_config: AuthConfig | None = None
_auth_initialized = False
_auth_init_error: str | None = None


def get_config(get_auth_config_fn) -> AuthConfig:
    global _auth_config
    if _auth_config is None:
        _auth_config = get_auth_config_fn()
    return _auth_config


def bootstrap_superadmin(
    config: AuthConfig,
    *,
    count_users_fn,
    create_user_fn,
    hash_password_fn,
) -> None:
    existing_users = count_users_fn(config.database_url)
    if existing_users > 0:
        return

    email = config.bootstrap_superadmin_email.strip().lower()
    username = config.bootstrap_superadmin_username.strip().lower()
    password = config.bootstrap_superadmin_password

    has_any_bootstrap_field = any([email, username, password])
    has_all_bootstrap_fields = bool(email and username and password)

    if has_any_bootstrap_field and not has_all_bootstrap_fields:
        print(
            "[WARN] Incomplete superadmin bootstrap env vars; skipping bootstrap user creation."
        )
        return

    if not has_all_bootstrap_fields:
        return

    create_user_fn(
        config.database_url,
        email=email,
        username=username,
        password_hash=hash_password_fn(password),
        role="superadmin",
        is_active=True,
    )
    print("[INFO] Bootstrap superadmin user created from environment.")


def ensure_auth_initialized(
    *,
    app_logger,
    get_config_fn,
    run_auth_schema_migration_fn,
    bootstrap_superadmin_fn,
    ensure_download_worker_started_fn,
) -> bool:
    global _auth_initialized, _auth_init_error

    if _auth_initialized:
        return True
    if _auth_init_error is not None:
        return False

    try:
        config = get_config_fn()
        run_auth_schema_migration_fn(config.database_url)
        bootstrap_superadmin_fn(config)
        ensure_download_worker_started_fn()
        _auth_initialized = True
        return True
    except Exception as exc:  # pragma: no cover - guarded by endpoint behavior tests
        _auth_init_error = str(exc)
        app_logger.error("Auth initialization failed: %s", exc)
        return False


def auth_ready_or_503(*, ensure_auth_initialized_fn, json_error_fn):
    if ensure_auth_initialized_fn():
        return None
    return json_error_fn(503, "auth_unavailable", "Authentication system unavailable")
