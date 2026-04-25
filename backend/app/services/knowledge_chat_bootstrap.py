from __future__ import annotations

from ..repositories.registry import create_registry_entity, create_registry_version, create_share_grant, find_registry_entity
from ..repositories.users import list_users
from .agent_prompt_defaults import default_agent_runtime_prompts

KNOWLEDGE_CHAT_AGENT_ID = "agent.knowledge_chat"
_KNOWLEDGE_CHAT_AGENT_SPEC = {
    "name": "Knowledge Chat",
    "description": "Product-facing knowledge-backed chat agent.",
    "instructions": "Answer using retrieved knowledge when it is relevant and available.",
    "runtime_prompts": default_agent_runtime_prompts(),
    "default_model_ref": None,
    "tool_refs": [],
    "runtime_constraints": {
        "internet_required": False,
        "sandbox_required": False,
    },
}


def _select_owner_user_id(database_url: str) -> int | None:
    users = list_users(database_url, is_active=True)
    if not users:
        users = list_users(database_url, is_active=None)
    if not users:
        return None

    for user in users:
        if str(user.get("role", "")).strip().lower() == "superadmin":
            return int(user["id"])
    return int(users[0]["id"])


def ensure_knowledge_chat_agent(database_url: str) -> bool:
    existing = find_registry_entity(database_url, entity_type="agent", entity_id=KNOWLEDGE_CHAT_AGENT_ID)
    owner_user_id = int(existing["owner_user_id"]) if existing and existing.get("owner_user_id") is not None else _select_owner_user_id(database_url)
    if owner_user_id is None:
        return False

    if existing is None:
        create_registry_entity(
            database_url,
            entity_id=KNOWLEDGE_CHAT_AGENT_ID,
            entity_type="agent",
            owner_user_id=owner_user_id,
            visibility="private",
            status="draft",
        )
        create_registry_version(
            database_url,
            entity_id=KNOWLEDGE_CHAT_AGENT_ID,
            version="v1",
            spec_json=dict(_KNOWLEDGE_CHAT_AGENT_SPEC),
            set_current=True,
            published=True,
        )
    elif existing.get("current_version") is None:
        create_registry_version(
            database_url,
            entity_id=KNOWLEDGE_CHAT_AGENT_ID,
            version="v1",
            spec_json=dict(_KNOWLEDGE_CHAT_AGENT_SPEC),
            set_current=True,
            published=True,
        )

    create_share_grant(
        database_url,
        entity_id=KNOWLEDGE_CHAT_AGENT_ID,
        grantee_type="public",
        grantee_id=None,
        permission="execute",
        shared_by_user_id=owner_user_id,
    )
    return True
