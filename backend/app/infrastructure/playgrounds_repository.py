from __future__ import annotations

from typing import Any

from ..repositories import chat_conversations as chat_repository


def list_sessions(
    database_url: str,
    *,
    owner_user_id: int,
    conversation_kind: str,
) -> list[dict[str, Any]]:
    return chat_repository.list_conversation_summaries(
        database_url,
        owner_user_id=owner_user_id,
        conversation_kind=conversation_kind,
    )


def get_session(
    database_url: str,
    *,
    owner_user_id: int,
    conversation_id: str,
    conversation_kind: str,
) -> dict[str, Any] | None:
    return chat_repository.get_conversation(
        database_url,
        owner_user_id=owner_user_id,
        conversation_id=conversation_id,
        conversation_kind=conversation_kind,
    )


def list_messages(
    database_url: str,
    *,
    conversation_id: str,
) -> list[dict[str, Any]]:
    return chat_repository.list_messages(database_url, conversation_id=conversation_id)


def create_session(
    database_url: str,
    *,
    owner_user_id: int,
    title: str,
    title_source: str,
    assistant_ref: str | None,
    model_id: str | None,
    knowledge_base_id: str | None,
    conversation_kind: str,
) -> dict[str, Any]:
    return chat_repository.create_conversation(
        database_url,
        owner_user_id=owner_user_id,
        title=title,
        title_source=title_source,
        assistant_ref=assistant_ref,
        model_id=model_id,
        knowledge_base_id=knowledge_base_id,
        conversation_kind=conversation_kind,
    )


def update_session(
    database_url: str,
    *,
    owner_user_id: int,
    conversation_id: str,
    title: object = chat_repository._UNSET,
    title_source: object = chat_repository._UNSET,
    assistant_ref: object = chat_repository._UNSET,
    model_id: object = chat_repository._UNSET,
    knowledge_base_id: object = chat_repository._UNSET,
    conversation_kind: str,
) -> dict[str, Any] | None:
    return chat_repository.update_conversation(
        database_url,
        owner_user_id=owner_user_id,
        conversation_id=conversation_id,
        title=title,
        title_source=title_source,
        assistant_ref=assistant_ref,
        model_id=model_id,
        knowledge_base_id=knowledge_base_id,
        conversation_kind=conversation_kind,
    )


def delete_session(
    database_url: str,
    *,
    owner_user_id: int,
    conversation_id: str,
    conversation_kind: str,
) -> bool:
    return chat_repository.delete_conversation(
        database_url,
        owner_user_id=owner_user_id,
        conversation_id=conversation_id,
        conversation_kind=conversation_kind,
    )


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
    conversation_kind: str,
) -> dict[str, Any] | None:
    return chat_repository.append_message_pair(
        database_url,
        owner_user_id=owner_user_id,
        conversation_id=conversation_id,
        user_content=user_content,
        assistant_content=assistant_content,
        user_metadata=user_metadata,
        assistant_metadata=assistant_metadata,
        conversation_title=conversation_title,
        title_source=title_source,
        conversation_kind=conversation_kind,
    )
