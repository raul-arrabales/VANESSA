from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import psycopg

from ..db import get_connection

PLAIN_CONVERSATION_KIND = "plain"
KNOWLEDGE_CONVERSATION_KIND = "knowledge"
_UNSET = object()


def _conversation_select_sql() -> str:
    return """
        SELECT
            c.id,
            c.owner_user_id,
            c.conversation_kind,
            c.title,
            c.title_source,
            c.assistant_ref,
            c.model_id,
            c.knowledge_base_id,
            c.created_at,
            c.updated_at,
            COALESCE((
                SELECT COUNT(*)
                FROM chat_messages AS m
                WHERE m.conversation_id = c.id
            ), 0) AS message_count
        FROM chat_conversations AS c
    """


def list_conversation_summaries(
    database_url: str,
    *,
    owner_user_id: int,
    conversation_kind: str = PLAIN_CONVERSATION_KIND,
) -> list[dict[str, Any]]:
    query = _conversation_select_sql() + """
        WHERE c.owner_user_id = %s AND c.conversation_kind = %s
        ORDER BY c.updated_at DESC, c.created_at DESC, c.id DESC
    """
    with get_connection(database_url) as connection:
        rows = connection.execute(query, (owner_user_id, conversation_kind)).fetchall()
    return [dict(row) for row in rows]


def get_conversation(
    database_url: str,
    *,
    owner_user_id: int,
    conversation_id: str,
    conversation_kind: str = PLAIN_CONVERSATION_KIND,
) -> dict[str, Any] | None:
    query = _conversation_select_sql() + """
        WHERE c.id = %s AND c.owner_user_id = %s AND c.conversation_kind = %s
    """
    with get_connection(database_url) as connection:
        row = connection.execute(
            query,
            (conversation_id, owner_user_id, conversation_kind),
        ).fetchone()
    return dict(row) if row else None


def list_messages(
    database_url: str,
    *,
    conversation_id: str,
) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                conversation_id,
                message_index,
                role,
                content,
                metadata_json,
                created_at
            FROM chat_messages
            WHERE conversation_id = %s
            ORDER BY message_index ASC, created_at ASC, id ASC
            """,
            (conversation_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def create_conversation(
    database_url: str,
    *,
    owner_user_id: int,
    title: str,
    title_source: str,
    assistant_ref: str | None,
    model_id: str | None,
    knowledge_base_id: str | None,
    conversation_kind: str = PLAIN_CONVERSATION_KIND,
) -> dict[str, Any]:
    conversation_id = str(uuid4())
    now = datetime.now(tz=timezone.utc)
    with get_connection(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chat_conversations (
                    id,
                    owner_user_id,
                    conversation_kind,
                    title,
                    title_source,
                    assistant_ref,
                    model_id,
                    knowledge_base_id,
                    created_at,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    conversation_id,
                    owner_user_id,
                    conversation_kind,
                    title,
                    title_source,
                    assistant_ref,
                    model_id,
                    knowledge_base_id,
                    now,
                    now,
                ),
            )
    conversation = get_conversation(
        database_url,
        owner_user_id=owner_user_id,
        conversation_id=conversation_id,
        conversation_kind=conversation_kind,
    )
    if conversation is None:
        raise ValueError("conversation_create_failed")
    return conversation


def update_conversation(
    database_url: str,
    *,
    owner_user_id: int,
    conversation_id: str,
    title: object = _UNSET,
    title_source: object = _UNSET,
    assistant_ref: object = _UNSET,
    model_id: object = _UNSET,
    knowledge_base_id: object = _UNSET,
    conversation_kind: str = PLAIN_CONVERSATION_KIND,
) -> dict[str, Any] | None:
    assignments: list[str] = []
    params: list[object] = []

    if title is not _UNSET:
        assignments.append("title = %s")
        params.append(title)
    if title_source is not _UNSET:
        assignments.append("title_source = %s")
        params.append(title_source)
    if assistant_ref is not _UNSET:
        assignments.append("assistant_ref = %s")
        params.append(assistant_ref)
    if model_id is not _UNSET:
        assignments.append("model_id = %s")
        params.append(model_id)
    if knowledge_base_id is not _UNSET:
        assignments.append("knowledge_base_id = %s")
        params.append(knowledge_base_id)

    if not assignments:
        return get_conversation(
            database_url,
            owner_user_id=owner_user_id,
            conversation_id=conversation_id,
            conversation_kind=conversation_kind,
        )

    assignments.append("updated_at = %s")
    params.append(datetime.now(tz=timezone.utc))
    params.extend((conversation_id, owner_user_id, conversation_kind))

    with get_connection(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE chat_conversations
                SET {", ".join(assignments)}
                WHERE id = %s AND owner_user_id = %s AND conversation_kind = %s
                """,
                params,
            )
            if cursor.rowcount == 0:
                return None
    return get_conversation(
        database_url,
        owner_user_id=owner_user_id,
        conversation_id=conversation_id,
        conversation_kind=conversation_kind,
    )


def delete_conversation(
    database_url: str,
    *,
    owner_user_id: int,
    conversation_id: str,
    conversation_kind: str = PLAIN_CONVERSATION_KIND,
) -> bool:
    with get_connection(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM chat_conversations
                WHERE id = %s AND owner_user_id = %s AND conversation_kind = %s
                """,
                (conversation_id, owner_user_id, conversation_kind),
            )
            return cursor.rowcount > 0


def append_message_pair(
    database_url: str,
    *,
    owner_user_id: int,
    conversation_id: str,
    user_content: str,
    assistant_content: str,
    user_metadata: dict[str, Any] | None = None,
    assistant_metadata: dict[str, Any] | None = None,
    conversation_title: str | None = None,
    title_source: str | None = None,
    conversation_kind: str = PLAIN_CONVERSATION_KIND,
) -> dict[str, Any] | None:
    user_metadata = user_metadata or {}
    assistant_metadata = assistant_metadata or {}
    now = datetime.now(tz=timezone.utc)
    user_message_id = str(uuid4())
    assistant_message_id = str(uuid4())

    with get_connection(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM chat_conversations
                WHERE id = %s AND owner_user_id = %s AND conversation_kind = %s
                FOR UPDATE
                """,
                (conversation_id, owner_user_id, conversation_kind),
            )
            locked_row = cursor.fetchone()
            if locked_row is None:
                return None

            cursor.execute(
                """
                SELECT COALESCE(MAX(message_index), -1) AS max_index
                FROM chat_messages
                WHERE conversation_id = %s
                """,
                (conversation_id,),
            )
            max_index_row = cursor.fetchone() or {"max_index": -1}
            next_index = int(max_index_row["max_index"]) + 1

            update_assignments = ["updated_at = %s"]
            update_params: list[object] = [now]
            if conversation_title is not None:
                update_assignments.append("title = %s")
                update_params.append(conversation_title)
            if title_source is not None:
                update_assignments.append("title_source = %s")
                update_params.append(title_source)
            update_params.extend((conversation_id, owner_user_id, conversation_kind))

            cursor.execute(
                f"""
                UPDATE chat_conversations
                SET {", ".join(update_assignments)}
                WHERE id = %s AND owner_user_id = %s AND conversation_kind = %s
                """,
                update_params,
            )

            cursor.execute(
                """
                INSERT INTO chat_messages (
                    id,
                    conversation_id,
                    message_index,
                    role,
                    content,
                    metadata_json,
                    created_at
                )
                VALUES (%s, %s, %s, 'user', %s, %s::jsonb, %s)
                RETURNING
                    id,
                    conversation_id,
                    message_index,
                    role,
                    content,
                    metadata_json,
                    created_at
                """,
                (
                    user_message_id,
                    conversation_id,
                    next_index,
                    user_content,
                    psycopg.types.json.Jsonb(user_metadata),
                    now,
                ),
            )
            user_message = dict(cursor.fetchone() or {})

            cursor.execute(
                """
                INSERT INTO chat_messages (
                    id,
                    conversation_id,
                    message_index,
                    role,
                    content,
                    metadata_json,
                    created_at
                )
                VALUES (%s, %s, %s, 'assistant', %s, %s::jsonb, %s)
                RETURNING
                    id,
                    conversation_id,
                    message_index,
                    role,
                    content,
                    metadata_json,
                    created_at
                """,
                (
                    assistant_message_id,
                    conversation_id,
                    next_index + 1,
                    assistant_content,
                    psycopg.types.json.Jsonb(assistant_metadata),
                    now,
                ),
            )
            assistant_message = dict(cursor.fetchone() or {})

            cursor.execute(
                _conversation_select_sql()
                + """
                    WHERE c.id = %s AND c.owner_user_id = %s AND c.conversation_kind = %s
                """,
                (conversation_id, owner_user_id, conversation_kind),
            )
            conversation = cursor.fetchone()

    if conversation is None:
        return None

    return {
        "conversation": dict(conversation),
        "messages": [user_message, assistant_message],
    }
