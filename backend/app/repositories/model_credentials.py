from __future__ import annotations

from typing import Any
from uuid import UUID

from ..db import get_connection

_ALLOWED_SCOPES = {"platform", "personal"}


def list_credentials_for_user(
    database_url: str,
    *,
    requester_user_id: int,
    requester_role: str,
) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        if requester_role == "superadmin":
            rows = connection.execute(
                """
                SELECT id, owner_user_id, credential_scope, provider_slug, display_name, api_base_url,
                       api_key_last4, is_active, created_by_user_id, revoked_at, created_at, updated_at
                FROM model_provider_credentials
                WHERE is_active = TRUE
                ORDER BY created_at DESC
                """
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT id, owner_user_id, credential_scope, provider_slug, display_name, api_base_url,
                       api_key_last4, is_active, created_by_user_id, revoked_at, created_at, updated_at
                FROM model_provider_credentials
                WHERE owner_user_id = %s AND is_active = TRUE
                ORDER BY created_at DESC
                """,
                (requester_user_id,),
            ).fetchall()
    return [dict(row) for row in rows]


def create_credential(
    database_url: str,
    *,
    owner_user_id: int,
    credential_scope: str,
    provider_slug: str,
    display_name: str,
    api_base_url: str | None,
    api_key: str,
    encryption_key: str,
    created_by_user_id: int,
) -> dict[str, Any]:
    scope = credential_scope.strip().lower()
    if scope not in _ALLOWED_SCOPES:
        raise ValueError("invalid_credential_scope")

    provider = provider_slug.strip().lower()
    if not provider:
        raise ValueError("invalid_provider")

    key_value = api_key.strip()
    if not key_value:
        raise ValueError("invalid_api_key")

    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO model_provider_credentials (
                owner_user_id, credential_scope, provider_slug, display_name,
                api_base_url, api_key_encrypted, api_key_last4, created_by_user_id
            )
            VALUES (
                %s, %s, %s, %s, %s,
                pgp_sym_encrypt(%s, %s),
                %s,
                %s
            )
            RETURNING id, owner_user_id, credential_scope, provider_slug, display_name,
                      api_base_url, api_key_last4, is_active, created_by_user_id,
                      revoked_at, created_at, updated_at
            """,
            (
                owner_user_id,
                scope,
                provider,
                display_name.strip(),
                api_base_url.strip() if api_base_url else None,
                key_value,
                encryption_key,
                key_value[-4:],
                created_by_user_id,
            ),
        ).fetchone()
    if row is None:
        raise RuntimeError("failed_to_create_credential")
    return dict(row)


def revoke_credential(
    database_url: str,
    *,
    credential_id: str,
    owner_user_id: int,
) -> dict[str, Any] | None:
    parsed = UUID(credential_id)
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            UPDATE model_provider_credentials
            SET is_active = FALSE, revoked_at = NOW(), updated_at = NOW()
            WHERE id = %s AND owner_user_id = %s AND is_active = TRUE
            RETURNING id, owner_user_id, credential_scope, provider_slug, display_name,
                      api_base_url, api_key_last4, is_active, created_by_user_id,
                      revoked_at, created_at, updated_at
            """,
            (str(parsed), owner_user_id),
        ).fetchone()
    return dict(row) if row else None


def get_active_credential_secret(
    database_url: str,
    *,
    credential_id: str,
    requester_user_id: int,
    requester_role: str,
    encryption_key: str,
) -> dict[str, Any] | None:
    parsed = UUID(credential_id)
    with get_connection(database_url) as connection:
        if requester_role in {"superadmin", "admin"}:
            row = connection.execute(
                """
                SELECT id, owner_user_id, credential_scope, provider_slug, display_name, api_base_url,
                       pgp_sym_decrypt(api_key_encrypted, %s) AS api_key
                FROM model_provider_credentials
                WHERE id = %s AND is_active = TRUE
                """,
                (encryption_key, str(parsed)),
            ).fetchone()
        else:
            row = connection.execute(
                """
                SELECT id, owner_user_id, credential_scope, provider_slug, display_name, api_base_url,
                       pgp_sym_decrypt(api_key_encrypted, %s) AS api_key
                FROM model_provider_credentials
                WHERE id = %s AND owner_user_id = %s AND is_active = TRUE
                """,
                (encryption_key, str(parsed), requester_user_id),
            ).fetchone()
    return dict(row) if row else None
