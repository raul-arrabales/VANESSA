from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AuthConfig:
    database_url: str
    jwt_secret: str
    jwt_algorithm: str
    access_token_ttl_seconds: int
    allow_self_register: bool
    bootstrap_superadmin_email: str
    bootstrap_superadmin_username: str
    bootstrap_superadmin_password: str
    flask_env: str
    model_storage_root: str = "/models/llm"
    model_download_max_workers: int = 2
    model_download_stale_seconds: int = 900
    model_download_allow_patterns_default: str = ""
    model_download_ignore_patterns_default: str = ""
    hf_token: str = ""


def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def get_auth_config() -> AuthConfig:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set")

    flask_env = os.getenv("FLASK_ENV", "development").strip().lower() or "development"

    jwt_secret = os.getenv("AUTH_JWT_SECRET", "").strip()
    if not jwt_secret:
        if flask_env == "development":
            jwt_secret = "insecure-dev-only-secret"
            print("[WARN] AUTH_JWT_SECRET not set; using insecure development fallback.")
        else:
            raise RuntimeError("AUTH_JWT_SECRET must be set outside development")

    return AuthConfig(
        database_url=database_url,
        jwt_secret=jwt_secret,
        jwt_algorithm=os.getenv("AUTH_JWT_ALGORITHM", "HS256").strip() or "HS256",
        access_token_ttl_seconds=_get_int_env("AUTH_ACCESS_TOKEN_TTL_SECONDS", 28_800),
        allow_self_register=_get_bool_env("AUTH_ALLOW_SELF_REGISTER", True),
        bootstrap_superadmin_email=os.getenv("AUTH_BOOTSTRAP_SUPERADMIN_EMAIL", "").strip(),
        bootstrap_superadmin_username=os.getenv("AUTH_BOOTSTRAP_SUPERADMIN_USERNAME", "").strip(),
        bootstrap_superadmin_password=os.getenv("AUTH_BOOTSTRAP_SUPERADMIN_PASSWORD", ""),
        flask_env=flask_env,
        model_storage_root=os.getenv("MODEL_STORAGE_ROOT", "/models/llm").strip() or "/models/llm",
        model_download_max_workers=_get_int_env("MODEL_DOWNLOAD_MAX_WORKERS", 2),
        model_download_stale_seconds=_get_int_env("MODEL_DOWNLOAD_STALE_SECONDS", 900),
        model_download_allow_patterns_default=os.getenv("MODEL_DOWNLOAD_ALLOW_PATTERNS_DEFAULT", "").strip(),
        model_download_ignore_patterns_default=os.getenv("MODEL_DOWNLOAD_IGNORE_PATTERNS_DEFAULT", "").strip(),
        hf_token=os.getenv("HF_TOKEN", "").strip(),
    )
