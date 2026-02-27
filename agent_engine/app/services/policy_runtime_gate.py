from __future__ import annotations

from typing import Any

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    psycopg = None
    dict_row = None

try:  # pragma: no cover - import path varies by invocation style
    from ..config import DEFAULT_RUNTIME_PROFILE, RUNTIME_PROFILES, get_config
except ImportError:  # pragma: no cover
    from agent_engine.app.config import DEFAULT_RUNTIME_PROFILE, RUNTIME_PROFILES, get_config


class ExecutionBlockedError(RuntimeError):
    def __init__(self, *, code: str, message: str, status_code: int, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def _database_url() -> str:
    return get_config().database_url


def _db_available() -> bool:
    return bool(psycopg is not None and dict_row is not None and _database_url())


def _connect():
    return psycopg.connect(_database_url(), row_factory=dict_row)


def _runtime_profile_from_env() -> str | None:
    env_value = get_config().runtime_profile_override
    return env_value if env_value in RUNTIME_PROFILES else None


def resolve_runtime_profile(requested_profile: str | None) -> str:
    normalized_requested = str(requested_profile or "").strip().lower()
    if normalized_requested in RUNTIME_PROFILES:
        return normalized_requested

    env_value = _runtime_profile_from_env()
    if env_value:
        return env_value

    if _db_available():
        try:
            with _connect() as connection:
                row = connection.execute(
                    "SELECT config_value FROM system_runtime_config WHERE config_key = 'runtime_profile'"
                ).fetchone()
                value = str((row or {}).get("config_value", "")).strip().lower()
                if value in RUNTIME_PROFILES:
                    return value
        except Exception:
            pass

    return DEFAULT_RUNTIME_PROFILE


def _get_entity(*, entity_type: str, entity_id: str) -> dict[str, Any] | None:
    if not _db_available():
        return None
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT e.*, v.version AS current_version, v.spec_json AS current_spec, v.published_at
            FROM registry_entities e
            LEFT JOIN registry_versions v
              ON v.entity_id = e.entity_id AND v.is_current = TRUE
            WHERE e.entity_type = %s AND e.entity_id = %s
            """,
            (entity_type, entity_id),
        ).fetchone()
    return dict(row) if row else None


def _evaluate_policy(*, user_id: int, entity_id: str, action: str) -> str | None:
    if not _db_available():
        return None
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT effect, rule_json
            FROM policy_rules
            WHERE scope_type = 'user'
              AND scope_id = %s
              AND resource_type = 'entity'
              AND (resource_id = %s OR resource_id = '*')
            ORDER BY created_at DESC
            """,
            (str(user_id), entity_id),
        ).fetchall()

    decision: str | None = None
    for row in rows:
        rule_json = row.get("rule_json") if isinstance(row.get("rule_json"), dict) else {}
        rule_action = str(rule_json.get("action", "*")).strip().lower() or "*"
        if rule_action not in {"*", action}:
            continue
        effect = str(row.get("effect", "")).strip().lower()
        if effect == "deny":
            return "deny"
        if effect == "allow":
            decision = "allow"
    return decision


def _list_permissions_for_user(*, entity_id: str, user_id: int) -> set[str]:
    if not _db_available():
        return set()

    with _connect() as connection:
        entity_row = connection.execute(
            "SELECT owner_user_id, visibility FROM registry_entities WHERE entity_id = %s",
            (entity_id,),
        ).fetchone()
        if entity_row is None:
            return set()

        owner_user_id = entity_row.get("owner_user_id")
        visibility = str(entity_row.get("visibility", "private")).strip().lower()
        permissions: set[str] = set()
        if owner_user_id is not None and int(owner_user_id) == int(user_id):
            return {"view", "fork", "execute", "admin"}
        if visibility in {"public", "unlisted"}:
            permissions.add("view")

        rows = connection.execute(
            """
            SELECT permission
            FROM entity_shares
            WHERE entity_id = %s
              AND ((grantee_type = 'public') OR (grantee_type = 'user' AND grantee_id = %s))
            """,
            (entity_id, str(user_id)),
        ).fetchall()
    for row in rows:
        permission = str(row.get("permission", "")).strip().lower()
        if permission in {"view", "fork", "execute", "admin"}:
            permissions.add(permission)
    return permissions


def require_agent_execute_permission(*, user_id: int, user_role: str, agent_id: str) -> None:
    if user_role.strip().lower() == "superadmin":
        return
    if not _db_available():
        return

    decision = _evaluate_policy(user_id=user_id, entity_id=agent_id, action="execute")
    if decision == "deny":
        raise ExecutionBlockedError(
            code="EXEC_POLICY_DENIED",
            message=f"Policy denies execute permission for agent '{agent_id}'",
            status_code=403,
        )

    permissions = _list_permissions_for_user(entity_id=agent_id, user_id=user_id)
    if "admin" in permissions or "execute" in permissions or decision == "allow":
        return

    raise ExecutionBlockedError(
        code="EXEC_POLICY_DENIED",
        message=f"Missing execute permission for agent '{agent_id}'",
        status_code=403,
    )


def resolve_agent_spec(*, agent_id: str) -> dict[str, Any]:
    entity = _get_entity(entity_type="agent", entity_id=agent_id)
    if entity is None:
        if _db_available():
            raise ExecutionBlockedError(
                code="EXEC_AGENT_NOT_FOUND",
                message=f"Agent '{agent_id}' not found",
                status_code=404,
            )
        return {
            "entity_id": agent_id,
            "current_version": "v1",
            "current_spec": {
                "name": agent_id,
                "description": "in-memory agent",
                "instructions": "",
                "default_model_ref": None,
                "tool_refs": [],
                "runtime_constraints": {},
            },
        }
    return entity


def validate_runtime_and_dependencies(*, agent_entity: dict[str, Any], runtime_profile: str) -> tuple[str, str | None]:
    current_spec = agent_entity.get("current_spec") if isinstance(agent_entity.get("current_spec"), dict) else {}
    runtime_constraints = (
        current_spec.get("runtime_constraints")
        if isinstance(current_spec.get("runtime_constraints"), dict)
        else {}
    )

    internet_required = bool(runtime_constraints.get("internet_required", False))
    if internet_required and runtime_profile != "online":
        raise ExecutionBlockedError(
            code="EXEC_RUNTIME_PROFILE_BLOCKED",
            message=f"Agent '{agent_entity.get('entity_id', '')}' requires internet for profile '{runtime_profile}'",
            status_code=403,
        )

    model_ref_raw = current_spec.get("default_model_ref")
    model_ref = str(model_ref_raw).strip() if model_ref_raw is not None else None
    model_ref = model_ref if model_ref else None
    if model_ref and _db_available():
        model = _get_entity(entity_type="model", entity_id=model_ref)
        if model is None:
            raise ExecutionBlockedError(
                code="EXEC_MODEL_NOT_ALLOWED",
                message=f"Model '{model_ref}' referenced by agent does not exist",
                status_code=403,
            )

    tool_refs = current_spec.get("tool_refs") if isinstance(current_spec.get("tool_refs"), list) else []
    if runtime_profile != "online":
        for tool_ref in tool_refs:
            tool_id = str(tool_ref).strip()
            if not tool_id:
                continue
            tool = _get_entity(entity_type="tool", entity_id=tool_id) if _db_available() else None
            if tool is None and _db_available():
                raise ExecutionBlockedError(
                    code="EXEC_TOOL_NOT_ALLOWED",
                    message=f"Tool '{tool_id}' referenced by agent does not exist",
                    status_code=403,
                )
            tool_spec = tool.get("current_spec") if isinstance((tool or {}).get("current_spec"), dict) else {}
            if tool and not bool(tool_spec.get("offline_compatible", False)):
                raise ExecutionBlockedError(
                    code="EXEC_TOOL_NOT_ALLOWED",
                    message=f"Tool '{tool_id}' is not allowed for profile '{runtime_profile}'",
                    status_code=403,
                )

    return str(agent_entity.get("current_version", "v1") or "v1"), model_ref
