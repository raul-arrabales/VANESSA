from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..db import get_connection


def create_attachment(
    database_url: str,
    *,
    attachment_id: str,
    owner_user_id: int,
    mime_type: str,
    byte_size: int,
    sha256: str,
    width: int | None,
    height: int | None,
    storage_path: str,
    original_filename: str | None = None,
    attachment_kind: str = "image",
) -> dict[str, Any]:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO chat_attachments (
                id,
                owner_user_id,
                attachment_kind,
                mime_type,
                byte_size,
                sha256,
                width,
                height,
                storage_path,
                original_filename,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING
                id,
                owner_user_id,
                conversation_id,
                message_id,
                attachment_kind,
                mime_type,
                byte_size,
                sha256,
                width,
                height,
                storage_path,
                original_filename,
                created_at
            """,
            (
                attachment_id,
                owner_user_id,
                attachment_kind,
                mime_type,
                byte_size,
                sha256,
                width,
                height,
                storage_path,
                original_filename,
                datetime.now(tz=timezone.utc),
            ),
        ).fetchone()
    return dict(row)


def get_attachment(
    database_url: str,
    *,
    owner_user_id: int,
    attachment_id: str,
) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT
                id,
                owner_user_id,
                conversation_id,
                message_id,
                attachment_kind,
                mime_type,
                byte_size,
                sha256,
                width,
                height,
                storage_path,
                original_filename,
                created_at
            FROM chat_attachments
            WHERE id = %s AND owner_user_id = %s
            """,
            (attachment_id, owner_user_id),
        ).fetchone()
    return dict(row) if row else None


def list_attachments_by_ids(
    database_url: str,
    *,
    owner_user_id: int,
    attachment_ids: list[str],
) -> list[dict[str, Any]]:
    if not attachment_ids:
        return []
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                owner_user_id,
                conversation_id,
                message_id,
                attachment_kind,
                mime_type,
                byte_size,
                sha256,
                width,
                height,
                storage_path,
                original_filename,
                created_at
            FROM chat_attachments
            WHERE owner_user_id = %s AND id = ANY(%s::uuid[])
            """,
            (owner_user_id, attachment_ids),
        ).fetchall()
    return [dict(row) for row in rows]


def bind_attachments_to_message(
    database_url: str,
    *,
    owner_user_id: int,
    attachment_ids: list[str],
    conversation_id: str,
    message_id: str,
) -> None:
    if not attachment_ids:
        return
    with get_connection(database_url) as connection:
        connection.execute(
            """
            UPDATE chat_attachments
            SET conversation_id = %s,
                message_id = %s
            WHERE owner_user_id = %s
              AND id = ANY(%s::uuid[])
            """,
            (conversation_id, message_id, owner_user_id, attachment_ids),
        )
