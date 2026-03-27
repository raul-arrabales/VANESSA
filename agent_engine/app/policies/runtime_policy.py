from __future__ import annotations

from typing import Any

from ..services.policy_runtime_gate import (
    require_agent_execute_permission,
    resolve_agent_spec,
    resolve_agent_tools,
    validate_runtime_and_dependencies,
)


def require_agent_execute_permission_stage(*, user_id: int, user_role: str, agent_id: str) -> None:
    require_agent_execute_permission(user_id=user_id, user_role=user_role, agent_id=agent_id)


def resolve_agent_spec_stage(*, agent_id: str) -> dict[str, Any]:
    return resolve_agent_spec(agent_id=agent_id)


def validate_runtime_and_dependencies_stage(*, agent_entity: dict[str, Any], runtime_profile: str) -> tuple[str, str | None]:
    return validate_runtime_and_dependencies(agent_entity=agent_entity, runtime_profile=runtime_profile)


def resolve_agent_tools_stage(*, agent_entity: dict[str, Any], runtime_profile: str) -> list[dict[str, Any]]:
    return resolve_agent_tools(agent_entity=agent_entity, runtime_profile=runtime_profile)
