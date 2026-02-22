from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from .config import AuthConfig


TOKEN_PREFIX = "Bearer"


def issue_access_token(user: dict[str, Any], config: AuthConfig) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "username": user["username"],
        "role": user["role"],
        "iat": now,
        "exp": now + timedelta(seconds=config.access_token_ttl_seconds),
    }
    return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)


def decode_access_token(token: str, config: AuthConfig) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = jwt.decode(token, config.jwt_secret, algorithms=[config.jwt_algorithm])
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, "token_expired"
    except jwt.InvalidTokenError:
        return None, "invalid_token"
