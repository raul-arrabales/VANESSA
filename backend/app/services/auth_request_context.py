from __future__ import annotations

from typing import Any

from ..auth_tokens import TOKEN_PREFIX, decode_access_token
from ..repositories.users import find_user_by_id
from .auth_runtime import ensure_auth_initialized, get_config


def resolve_current_user_from_auth_header(
    auth_header: str,
    *,
    ensure_auth_initialized_fn=ensure_auth_initialized,
    get_config_fn=get_config,
    decode_access_token_fn=decode_access_token,
    find_user_by_id_fn=find_user_by_id,
) -> tuple[dict[str, Any] | None, str | None]:
    header = auth_header.strip()
    if not header:
        return None, None

    prefix = f"{TOKEN_PREFIX} "
    if not header.startswith(prefix):
        return None, "invalid_authorization_header"

    token = header[len(prefix) :].strip()
    if not token:
        return None, "missing_token"

    if not ensure_auth_initialized_fn():
        return None, "auth_unavailable"

    config = get_config_fn()
    payload, error = decode_access_token_fn(token, config)
    if payload is None:
        return None, error or "invalid_token"

    subject = str(payload.get("sub", "")).strip()
    if not subject.isdigit():
        return None, "invalid_token"

    user = find_user_by_id_fn(config.database_url, int(subject))
    if user is None:
        return None, "invalid_token"

    if not bool(user.get("is_active", False)):
        return None, "account_inactive"

    return user, None
