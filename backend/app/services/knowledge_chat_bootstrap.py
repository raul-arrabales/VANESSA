from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..repositories.registry import (
    create_registry_entity,
    create_registry_version,
    create_share_grant,
    find_registry_entity,
    list_registry_versions,
)
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


def _next_platform_agent_version(database_url: str, *, entity_id: str, current_version: object) -> str:
    version_numbers: list[int] = []
    for row in list_registry_versions(database_url, entity_id=entity_id):
        raw = str(row.get("version") or "").strip().lower()
        if raw.startswith("v") and raw[1:].isdigit():
            version_numbers.append(int(raw[1:]))
    raw_current = str(current_version or "").strip().lower()
    if raw_current.startswith("v") and raw_current[1:].isdigit():
        version_numbers.append(int(raw_current[1:]))
    return f"v{(max(version_numbers) if version_numbers else 1) + 1}"


def _reconcile_knowledge_chat_spec(current_spec: object) -> dict[str, Any]:
    current = deepcopy(current_spec) if isinstance(current_spec, dict) else {}
    reconciled = deepcopy(current)

    for key in ("name", "description", "instructions"):
        value = str(reconciled.get(key) or "").strip()
        if not value:
            reconciled[key] = _KNOWLEDGE_CHAT_AGENT_SPEC[key]

    runtime_prompts = reconciled.get("runtime_prompts")
    runtime_prompts = deepcopy(runtime_prompts) if isinstance(runtime_prompts, dict) else {}
    for key, value in _KNOWLEDGE_CHAT_AGENT_SPEC["runtime_prompts"].items():
        if not str(runtime_prompts.get(key) or "").strip():
            runtime_prompts[key] = value
    reconciled["runtime_prompts"] = runtime_prompts

    if "default_model_ref" not in reconciled:
        reconciled["default_model_ref"] = _KNOWLEDGE_CHAT_AGENT_SPEC["default_model_ref"]

    if not isinstance(reconciled.get("tool_refs"), list):
        reconciled["tool_refs"] = deepcopy(_KNOWLEDGE_CHAT_AGENT_SPEC["tool_refs"])

    runtime_constraints = reconciled.get("runtime_constraints")
    runtime_constraints = deepcopy(runtime_constraints) if isinstance(runtime_constraints, dict) else {}
    default_runtime_constraints = _KNOWLEDGE_CHAT_AGENT_SPEC["runtime_constraints"]
    for key, value in default_runtime_constraints.items():
        if not isinstance(runtime_constraints.get(key), bool):
            runtime_constraints[key] = value
    reconciled["runtime_constraints"] = runtime_constraints

    return reconciled


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
    else:
        current_spec = existing.get("current_spec") if isinstance(existing.get("current_spec"), dict) else {}
        reconciled_spec = _reconcile_knowledge_chat_spec(current_spec)
        if reconciled_spec != current_spec:
            create_registry_version(
                database_url,
                entity_id=KNOWLEDGE_CHAT_AGENT_ID,
                version=_next_platform_agent_version(
                    database_url,
                    entity_id=KNOWLEDGE_CHAT_AGENT_ID,
                    current_version=existing.get("current_version"),
                ),
                spec_json=reconciled_spec,
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
