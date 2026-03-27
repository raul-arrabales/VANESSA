from __future__ import annotations

from typing import Final

from ..services.knowledge_chat_bootstrap import KNOWLEDGE_CHAT_AGENT_ID

CHAT_PLAYGROUND_KIND: Final[str] = "chat"
KNOWLEDGE_PLAYGROUND_KIND: Final[str] = "knowledge"
CHAT_PLAYGROUND_ASSISTANT_REF: Final[str] = "assistant.playground.chat"
VANESSA_CORE_ASSISTANT_REF: Final[str] = "assistant.vanessa.core"

PLAYGROUND_KIND_TO_CONVERSATION_KIND: Final[dict[str, str]] = {
    CHAT_PLAYGROUND_KIND: "plain",
    KNOWLEDGE_PLAYGROUND_KIND: "knowledge",
}

CONVERSATION_KIND_TO_PLAYGROUND_KIND: Final[dict[str, str]] = {
    value: key for key, value in PLAYGROUND_KIND_TO_CONVERSATION_KIND.items()
}

PLAYGROUND_ASSISTANTS: Final[list[dict[str, object]]] = [
    {
        "assistant_ref": CHAT_PLAYGROUND_ASSISTANT_REF,
        "display_name": "Chat Assistant",
        "description": "General-purpose chat playground using your allowed models.",
        "playground_kind": CHAT_PLAYGROUND_KIND,
        "agent_id": None,
        "knowledge_required": False,
    },
    {
        "assistant_ref": VANESSA_CORE_ASSISTANT_REF,
        "display_name": "Vanessa Core",
        "description": "First-party Vanessa assistant running through the shared chat playground experience.",
        "playground_kind": CHAT_PLAYGROUND_KIND,
        "agent_id": None,
        "knowledge_required": False,
    },
    {
        "assistant_ref": KNOWLEDGE_CHAT_AGENT_ID,
        "display_name": "Knowledge Assistant",
        "description": "Knowledge-grounded playground backed by the active deployment bindings.",
        "playground_kind": KNOWLEDGE_PLAYGROUND_KIND,
        "agent_id": KNOWLEDGE_CHAT_AGENT_ID,
        "knowledge_required": True,
    },
]

_DEFAULT_ASSISTANT_REF_BY_KIND: Final[dict[str, str]] = {
    CHAT_PLAYGROUND_KIND: CHAT_PLAYGROUND_ASSISTANT_REF,
    KNOWLEDGE_PLAYGROUND_KIND: KNOWLEDGE_CHAT_AGENT_ID,
}


def conversation_kind_for_playground_kind(playground_kind: str) -> str:
    normalized = str(playground_kind).strip().lower()
    if normalized not in PLAYGROUND_KIND_TO_CONVERSATION_KIND:
        raise ValueError("invalid_playground_kind")
    return PLAYGROUND_KIND_TO_CONVERSATION_KIND[normalized]


def playground_kind_for_conversation_kind(conversation_kind: str) -> str:
    normalized = str(conversation_kind).strip().lower()
    return CONVERSATION_KIND_TO_PLAYGROUND_KIND.get(normalized, CHAT_PLAYGROUND_KIND)


def default_assistant_ref_for_kind(playground_kind: str) -> str:
    normalized = str(playground_kind).strip().lower()
    if normalized not in _DEFAULT_ASSISTANT_REF_BY_KIND:
        raise ValueError("invalid_playground_kind")
    return _DEFAULT_ASSISTANT_REF_BY_KIND[normalized]
