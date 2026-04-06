from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from psycopg.types.json import Jsonb

from ..db import get_connection

TASK_EMBEDDINGS = "embeddings"
TASK_LLM = "llm"
OWNER_PLATFORM = "platform"
OWNER_USER = "user"
LIFECYCLE_CREATED = "created"
LIFECYCLE_REGISTERED = "registered"
LIFECYCLE_VALIDATED = "validated"
LIFECYCLE_ACTIVE = "active"
LIFECYCLE_INACTIVE = "inactive"
LIFECYCLE_UNREGISTERED = "unregistered"
VALIDATION_FAILURE = "failure"
VALIDATION_SUCCESS = "success"
TEST_FAILURE = "failure"
TEST_SUCCESS = "success"


def infer_task_key(row: dict[str, Any]) -> str:
    explicit = str(row.get("task_key", "")).strip().lower()
    if explicit:
        return explicit
    return TASK_LLM


def infer_category(task_key: str) -> str:
    predictive_tasks = {
        TASK_EMBEDDINGS,
        "ocr",
        "vision",
        "speech_to_text",
        "classification",
        "regression",
        "ranking",
        "reranking",
        "moderation",
    }
    return "predictive" if task_key in predictive_tasks else "generative"


def infer_hosting_kind(row: dict[str, Any]) -> str:
    explicit = str(row.get("hosting_kind", "")).strip().lower()
    if explicit:
        return explicit
    return "local" if str(row.get("backend_kind", "")).strip().lower() == "local" else "cloud"


def infer_runtime_mode_policy(hosting_kind: str) -> str:
    return "online_offline" if hosting_kind == "local" else "online_only"


def infer_visibility_scope(row: dict[str, Any]) -> str:
    explicit = str(row.get("visibility_scope", "")).strip().lower()
    if explicit:
        return explicit
    return "private"


def infer_owner_type(row: dict[str, Any]) -> str:
    explicit = str(row.get("owner_type", "")).strip().lower()
    if explicit in {OWNER_PLATFORM, OWNER_USER}:
        return explicit
    if row.get("owner_user_id") is None:
        return OWNER_PLATFORM
    return OWNER_USER


def compute_config_fingerprint(row: dict[str, Any]) -> str:
    payload = {
        "provider": row.get("provider"),
        "provider_model_id": row.get("provider_model_id"),
        "source_id": row.get("source_id"),
        "local_path": row.get("local_path"),
        "backend_kind": row.get("backend_kind"),
        "availability": row.get("availability"),
        "credential_id": row.get("credential_id"),
        "task_key": infer_task_key(row),
        "hosting_kind": infer_hosting_kind(row),
        "checksum": row.get("checksum"),
        "revision": row.get("revision"),
        "metadata": row.get("metadata") or {},
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def upsert_model_record(
    database_url: str,
    *,
    model_id: str,
    node_id: str,
    name: str,
    provider: str,
    task_key: str,
    category: str,
    backend_kind: str,
    source_kind: str,
    availability: str,
    visibility_scope: str,
    owner_type: str,
    owner_user_id: int | None,
    provider_model_id: str | None,
    credential_id: str | None,
    source_id: str | None,
    local_path: str | None,
    status: str,
    lifecycle_state: str,
    metadata: dict[str, Any],
    comment: str | None,
    model_size_billion: float | None,
    created_by_user_id: int | None,
    registered_by_user_id: int | None,
    source: str | None = None,
    revision: str | None = None,
    checksum: str | None = None,
    model_version: str | None = None,
) -> dict[str, Any]:
    normalized_model_id = model_id.strip()
    normalized_task_key = task_key.strip().lower()
    normalized_category = category.strip().lower()
    normalized_backend_kind = backend_kind.strip().lower()
    normalized_source_kind = source_kind.strip().lower()
    normalized_availability = availability.strip().lower()
    normalized_visibility_scope = visibility_scope.strip().lower()
    normalized_owner_type = owner_type.strip().lower()
    hosting_kind = infer_hosting_kind({"backend_kind": normalized_backend_kind})
    runtime_mode_policy = infer_runtime_mode_policy(hosting_kind)
    fingerprint = compute_config_fingerprint(
        {
            "provider": provider,
            "provider_model_id": provider_model_id,
            "source_id": source_id,
            "local_path": local_path,
            "backend_kind": normalized_backend_kind,
            "availability": normalized_availability,
            "credential_id": credential_id,
            "task_key": normalized_task_key,
            "hosting_kind": hosting_kind,
            "checksum": checksum,
            "revision": revision,
            "metadata": metadata,
        }
    )

    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO model_registry (
                model_id,
                name,
                provider,
                source_id,
                local_path,
                status,
                metadata,
                created_by_user_id,
                registered_by_user_id,
                backend_kind,
                source_kind,
                availability,
                provider_model_id,
                credential_id,
                is_enabled,
                model_size_billion,
                comment,
                node_id,
                global_model_id,
                task_key,
                category,
                hosting_kind,
                runtime_mode_policy,
                lifecycle_state,
                visibility_scope,
                owner_user_id,
                owner_type,
                current_config_fingerprint,
                is_validation_current,
                last_validation_status,
                last_validated_at,
                last_validation_error,
                last_validation_config_fingerprint,
                source,
                revision,
                checksum,
                model_version,
                updated_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                FALSE, NULL, NULL, '{}'::jsonb, NULL, %s, %s, %s, %s, NOW()
            )
            ON CONFLICT (model_id)
            DO UPDATE SET
                name = EXCLUDED.name,
                provider = EXCLUDED.provider,
                source_id = EXCLUDED.source_id,
                local_path = EXCLUDED.local_path,
                status = EXCLUDED.status,
                metadata = EXCLUDED.metadata,
                registered_by_user_id = EXCLUDED.registered_by_user_id,
                backend_kind = EXCLUDED.backend_kind,
                source_kind = EXCLUDED.source_kind,
                availability = EXCLUDED.availability,
                provider_model_id = EXCLUDED.provider_model_id,
                credential_id = EXCLUDED.credential_id,
                is_enabled = EXCLUDED.is_enabled,
                model_size_billion = EXCLUDED.model_size_billion,
                comment = EXCLUDED.comment,
                node_id = EXCLUDED.node_id,
                global_model_id = EXCLUDED.global_model_id,
                task_key = EXCLUDED.task_key,
                category = EXCLUDED.category,
                hosting_kind = EXCLUDED.hosting_kind,
                runtime_mode_policy = EXCLUDED.runtime_mode_policy,
                lifecycle_state = EXCLUDED.lifecycle_state,
                visibility_scope = EXCLUDED.visibility_scope,
                owner_user_id = EXCLUDED.owner_user_id,
                owner_type = EXCLUDED.owner_type,
                current_config_fingerprint = EXCLUDED.current_config_fingerprint,
                is_validation_current = FALSE,
                last_validation_status = NULL,
                last_validated_at = NULL,
                last_validation_error = '{}'::jsonb,
                last_validation_config_fingerprint = NULL,
                source = EXCLUDED.source,
                revision = EXCLUDED.revision,
                checksum = EXCLUDED.checksum,
                model_version = EXCLUDED.model_version,
                updated_at = NOW()
            RETURNING *
            """,
            (
                normalized_model_id,
                name.strip(),
                provider.strip().lower(),
                source_id.strip() if source_id else None,
                local_path.strip() if local_path else None,
                status.strip().lower(),
                Jsonb(metadata),
                created_by_user_id,
                registered_by_user_id,
                normalized_backend_kind,
                normalized_source_kind,
                normalized_availability,
                provider_model_id.strip() if provider_model_id else None,
                credential_id,
                lifecycle_state.strip().lower() == LIFECYCLE_ACTIVE,
                model_size_billion,
                comment.strip() if comment else None,
                node_id.strip().lower(),
                f"{node_id.strip().lower()}:{normalized_model_id}",
                normalized_task_key,
                normalized_category,
                hosting_kind,
                runtime_mode_policy,
                lifecycle_state.strip().lower(),
                normalized_visibility_scope,
                owner_user_id if normalized_owner_type == OWNER_USER else None,
                normalized_owner_type,
                fingerprint,
                source.strip() if source else (source_id.strip() if source_id else None),
                revision.strip() if revision else None,
                checksum.strip() if checksum else None,
                model_version.strip() if model_version else None,
            ),
        ).fetchone()

        if local_path and local_path.strip():
            connection.execute(
                """
                INSERT INTO model_artifacts (
                    model_id,
                    artifact_type,
                    storage_path,
                    artifact_status,
                    provenance,
                    checksum,
                    runtime_requirements,
                    created_by_user_id
                )
                VALUES (%s, 'weights', %s, %s, %s, %s, %s::jsonb, %s)
                ON CONFLICT (model_id, artifact_type)
                DO UPDATE SET
                    storage_path = EXCLUDED.storage_path,
                    artifact_status = EXCLUDED.artifact_status,
                    provenance = EXCLUDED.provenance,
                    checksum = EXCLUDED.checksum,
                    runtime_requirements = EXCLUDED.runtime_requirements,
                    updated_at = NOW()
                """,
                (
                    normalized_model_id,
                    local_path.strip(),
                    "ready" if Path(local_path.strip()).exists() else "missing",
                    source_id.strip() if source_id else None,
                    checksum.strip() if checksum else None,
                    Jsonb({}),
                    created_by_user_id,
                ),
            )

    if row is None:
        raise RuntimeError("failed_to_upsert_model")
    return dict(row)


def list_catalog_models(database_url: str) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM model_registry
            ORDER BY updated_at DESC, model_id ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def list_local_artifacts(database_url: str) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT
                m.model_id,
                m.name,
                m.source_id,
                m.task_key,
                m.category,
                m.lifecycle_state,
                m.provider,
                m.metadata,
                m.updated_at,
                ma.artifact_type,
                ma.storage_path,
                ma.artifact_status,
                ma.provenance,
                ma.checksum,
                ma.runtime_requirements
            FROM model_registry m
            JOIN model_artifacts ma ON ma.model_id = m.model_id
            WHERE m.hosting_kind = 'local'
            ORDER BY m.updated_at DESC, m.model_id ASC, ma.artifact_type ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_model(database_url: str, model_id: str) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT
                m.*,
                (
                    SELECT jsonb_build_object(
                        'storage_path', ma.storage_path,
                        'artifact_status', ma.artifact_status,
                        'checksum', ma.checksum,
                        'provenance', ma.provenance,
                        'runtime_requirements', ma.runtime_requirements
                    )
                    FROM model_artifacts ma
                    WHERE ma.model_id = m.model_id
                    ORDER BY ma.updated_at DESC
                    LIMIT 1
                ) AS artifact,
                (
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'dependency_kind', d.dependency_kind,
                            'dependency_key', d.dependency_key,
                            'dependency_value', d.dependency_value,
                            'is_required', d.is_required,
                            'metadata', d.metadata
                        )
                        ORDER BY d.dependency_kind, d.dependency_key
                    )
                    FROM model_runtime_dependencies d
                    WHERE d.model_id = m.model_id
                ) AS dependencies
            FROM model_registry m
            WHERE m.model_id = %s
            """,
            (model_id.strip(),),
        ).fetchone()
    return dict(row) if row else None


def _eligible_clause(*, require_active: bool, capability_key: str | None) -> str:
    conditions = [
        "m.lifecycle_state <> 'deleted'",
    ]
    if require_active:
        conditions.extend(
            [
                "m.lifecycle_state = 'active'",
                "m.is_validation_current = TRUE",
                "m.last_validation_status = 'success'",
            ]
        )
    if capability_key == "embeddings":
        conditions.append("m.task_key = 'embeddings'")
    elif capability_key == "llm_inference":
        conditions.append("m.task_key = 'llm'")
    return " AND ".join(conditions)


def list_models_for_actor(
    database_url: str,
    *,
    actor_user_id: int,
    actor_role: str,
    runtime_profile: str,
    require_active: bool = False,
    capability_key: str | None = None,
) -> list[dict[str, Any]]:
    normalized_role = actor_role.strip().lower()
    eligible_clause = _eligible_clause(require_active=require_active, capability_key=capability_key)
    runtime_filter = """
        AND (
            %s <> 'offline'
            OR m.runtime_mode_policy = 'online_offline'
            OR m.hosting_kind = 'local'
            OR m.availability = 'offline_ready'
        )
    """

    base_projection = """
        SELECT DISTINCT
            m.*,
            COALESCE(
                (
                    SELECT jsonb_build_object(
                        'storage_path', ma.storage_path,
                        'artifact_status', ma.artifact_status,
                        'checksum', ma.checksum,
                        'provenance', ma.provenance,
                        'runtime_requirements', ma.runtime_requirements
                    )
                    FROM model_artifacts ma
                    WHERE ma.model_id = m.model_id
                    ORDER BY ma.updated_at DESC
                    LIMIT 1
                ),
                '{}'::jsonb
            ) AS artifact,
            COALESCE(
                (
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'dependency_kind', d.dependency_kind,
                            'dependency_key', d.dependency_key,
                            'dependency_value', d.dependency_value,
                            'is_required', d.is_required,
                            'metadata', d.metadata
                        )
                        ORDER BY d.dependency_kind, d.dependency_key
                    )
                    FROM model_runtime_dependencies d
                    WHERE d.model_id = m.model_id
                ),
                '[]'::jsonb
            ) AS dependencies
        FROM model_registry m
    """

    if normalized_role == "superadmin":
        query = f"""
            {base_projection}
            WHERE {eligible_clause}
            {runtime_filter}
            ORDER BY m.updated_at DESC, m.model_id ASC
        """
        params = (runtime_profile.strip().lower(),)
    else:
        query = f"""
            WITH user_role_cte AS (
                SELECT role
                FROM users
                WHERE id = %s
            ),
            user_groups_cte AS (
                SELECT group_id
                FROM user_group_memberships
                WHERE user_id = %s
            ),
            assigned_models AS (
                SELECT model_id FROM model_user_assignments WHERE user_id = %s
                UNION
                SELECT mga.model_id
                FROM model_group_assignments mga
                JOIN user_groups_cte ug ON ug.group_id = mga.group_id
                UNION
                SELECT model_id FROM model_global_assignments
                UNION
                SELECT jsonb_array_elements_text(msa.model_ids) AS model_id
                FROM model_scope_assignments msa
                JOIN user_role_cte ur ON ur.role = msa.scope
            )
            {base_projection}
            LEFT JOIN assigned_models a ON a.model_id = m.model_id
            WHERE
                {eligible_clause}
                AND (
                    (m.owner_type = 'user' AND m.owner_user_id = %s)
                    OR m.visibility_scope = 'platform'
                    OR (m.visibility_scope IN ('user', 'group') AND a.model_id IS NOT NULL)
                )
                {runtime_filter}
            ORDER BY m.updated_at DESC, m.model_id ASC
        """
        params = (
            actor_user_id,
            actor_user_id,
            actor_user_id,
            actor_user_id,
            runtime_profile.strip().lower(),
        )

    with get_connection(database_url) as connection:
        rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def list_model_picker_rows_for_actor(
    database_url: str,
    *,
    actor_user_id: int,
    actor_role: str,
    runtime_profile: str,
    require_active: bool = False,
    capability_key: str | None = None,
) -> list[dict[str, Any]]:
    normalized_role = actor_role.strip().lower()
    eligible_clause = _eligible_clause(require_active=require_active, capability_key=capability_key)
    runtime_filter = """
        AND (
            %s <> 'offline'
            OR m.runtime_mode_policy = 'online_offline'
            OR m.hosting_kind = 'local'
            OR m.availability = 'offline_ready'
        )
    """

    base_projection = """
        SELECT DISTINCT
            m.model_id,
            m.name,
            m.task_key,
            m.updated_at
        FROM model_registry m
    """

    if normalized_role == "superadmin":
        query = f"""
            {base_projection}
            WHERE {eligible_clause}
            {runtime_filter}
            ORDER BY m.updated_at DESC, m.model_id ASC
        """
        params = (runtime_profile.strip().lower(),)
    else:
        query = f"""
            WITH user_role_cte AS (
                SELECT role
                FROM users
                WHERE id = %s
            ),
            user_groups_cte AS (
                SELECT group_id
                FROM user_group_memberships
                WHERE user_id = %s
            ),
            assigned_models AS (
                SELECT model_id FROM model_user_assignments WHERE user_id = %s
                UNION
                SELECT mga.model_id
                FROM model_group_assignments mga
                JOIN user_groups_cte ug ON ug.group_id = mga.group_id
                UNION
                SELECT model_id FROM model_global_assignments
                UNION
                SELECT jsonb_array_elements_text(msa.model_ids) AS model_id
                FROM model_scope_assignments msa
                JOIN user_role_cte ur ON ur.role = msa.scope
            )
            {base_projection}
            LEFT JOIN assigned_models a ON a.model_id = m.model_id
            WHERE
                {eligible_clause}
                AND (
                    (m.owner_type = 'user' AND m.owner_user_id = %s)
                    OR m.visibility_scope = 'platform'
                    OR (m.visibility_scope IN ('user', 'group') AND a.model_id IS NOT NULL)
                )
                {runtime_filter}
            ORDER BY m.updated_at DESC, m.model_id ASC
        """
        params = (
            actor_user_id,
            actor_user_id,
            actor_user_id,
            actor_user_id,
            runtime_profile.strip().lower(),
        )

    with get_connection(database_url) as connection:
        rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def append_validation(
    database_url: str,
    *,
    model_id: str,
    validator_kind: str,
    trigger_reason: str,
    result: str,
    summary: str,
    error_details: dict[str, Any],
    config_fingerprint: str | None,
    validated_by_user_id: int | None,
) -> dict[str, Any]:
    with get_connection(database_url) as connection:
        validation = connection.execute(
            """
            INSERT INTO model_validations (
                model_id,
                validator_kind,
                trigger_reason,
                result,
                summary,
                error_details,
                config_fingerprint,
                validated_by_user_id
            )
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            RETURNING *
            """,
            (
                model_id.strip(),
                validator_kind.strip(),
                trigger_reason.strip(),
                result.strip(),
                summary.strip(),
                Jsonb(error_details),
                config_fingerprint,
                validated_by_user_id,
            ),
        ).fetchone()
        if result == VALIDATION_SUCCESS:
            lifecycle_state = LIFECYCLE_VALIDATED
            error_payload = {}
        else:
            current_state = get_model(database_url, model_id) or {}
            lifecycle_state = str(current_state.get("lifecycle_state", "")).strip().lower() or LIFECYCLE_REGISTERED
            if lifecycle_state == LIFECYCLE_ACTIVE:
                lifecycle_state = LIFECYCLE_INACTIVE
            error_payload = error_details
        connection.execute(
            """
            UPDATE model_registry
            SET
                is_validation_current = TRUE,
                last_validation_status = %s,
                last_validated_at = NOW(),
                last_validation_error = %s::jsonb,
                last_validation_config_fingerprint = %s,
                lifecycle_state = CASE
                    WHEN lifecycle_state = 'active' AND %s = 'success' THEN 'active'
                    ELSE %s
                END,
                updated_at = NOW()
            WHERE model_id = %s
            """,
            (
                result.strip(),
                Jsonb(error_payload),
                config_fingerprint,
                result.strip(),
                lifecycle_state,
                model_id.strip(),
            ),
        )
    return dict(validation) if validation else {}


def list_validation_history(database_url: str, *, model_id: str, limit: int = 10) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM model_validations
            WHERE model_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (model_id.strip(), limit),
        ).fetchall()
    return [dict(row) for row in rows]


def append_model_test_run(
    database_url: str,
    *,
    model_id: str,
    task_key: str,
    result: str,
    summary: str,
    input_payload: dict[str, Any],
    output_payload: dict[str, Any],
    error_details: dict[str, Any],
    latency_ms: float | None,
    config_fingerprint: str | None,
    tested_by_user_id: int | None,
) -> dict[str, Any]:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO model_test_runs (
                model_id,
                task_key,
                result,
                summary,
                input_payload,
                output_payload,
                error_details,
                latency_ms,
                config_fingerprint,
                tested_by_user_id
            )
            VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s)
            RETURNING *
            """,
            (
                model_id.strip(),
                task_key.strip().lower(),
                result.strip(),
                summary.strip(),
                Jsonb(input_payload),
                Jsonb(output_payload),
                Jsonb(error_details),
                latency_ms,
                config_fingerprint,
                tested_by_user_id,
            ),
        ).fetchone()
    return dict(row) if row else {}


def list_model_test_runs(database_url: str, *, model_id: str, limit: int = 10) -> list[dict[str, Any]]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM model_test_runs
            WHERE model_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (model_id.strip(), limit),
        ).fetchall()
    return [dict(row) for row in rows]


def get_model_test_run(database_url: str, test_run_id: str) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM model_test_runs
            WHERE id = %s::uuid
            """,
            (test_run_id.strip(),),
        ).fetchone()
    return dict(row) if row else None


def set_lifecycle_state(
    database_url: str,
    *,
    model_id: str,
    lifecycle_state: str,
) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            UPDATE model_registry
            SET
                lifecycle_state = %s,
                is_enabled = CASE WHEN %s = 'active' THEN TRUE ELSE is_enabled END,
                updated_at = NOW()
            WHERE model_id = %s
            RETURNING *
            """,
            (lifecycle_state.strip(), lifecycle_state.strip(), model_id.strip()),
        ).fetchone()
    return dict(row) if row else None


def activate_model(database_url: str, *, model_id: str) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            UPDATE model_registry
            SET lifecycle_state = 'active', is_enabled = TRUE, updated_at = NOW()
            WHERE model_id = %s
            RETURNING *
            """,
            (model_id.strip(),),
        ).fetchone()
    return dict(row) if row else None


def deactivate_model(database_url: str, *, model_id: str) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            UPDATE model_registry
            SET lifecycle_state = 'inactive', is_enabled = FALSE, updated_at = NOW()
            WHERE model_id = %s
            RETURNING *
            """,
            (model_id.strip(),),
        ).fetchone()
    return dict(row) if row else None


def mark_validation_stale(
    database_url: str,
    *,
    model_id: str,
) -> dict[str, Any] | None:
    with get_connection(database_url) as connection:
        row = connection.execute(
            """
            UPDATE model_registry
            SET
                is_validation_current = FALSE,
                lifecycle_state = CASE WHEN lifecycle_state = 'active' THEN 'inactive' ELSE lifecycle_state END,
                is_enabled = CASE WHEN lifecycle_state = 'active' THEN FALSE ELSE is_enabled END,
                updated_at = NOW()
            WHERE model_id = %s
            RETURNING *
            """,
            (model_id.strip(),),
        ).fetchone()
    return dict(row) if row else None


def delete_model(database_url: str, *, model_id: str) -> bool:
    with get_connection(database_url) as connection:
        row = connection.execute(
            "DELETE FROM model_registry WHERE model_id = %s RETURNING model_id",
            (model_id.strip(),),
        ).fetchone()
    return row is not None


def record_daily_usage(
    database_url: str,
    *,
    model_id: str,
    user_id: int | None,
    metric_key: str,
    metric_value: float,
    request_count: int = 0,
) -> None:
    with get_connection(database_url) as connection:
        connection.execute(
            """
            INSERT INTO model_usage_daily (
                usage_date,
                model_id,
                user_id,
                metric_key,
                metric_value,
                request_count,
                updated_at
            )
            VALUES (CURRENT_DATE, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (usage_date, model_id, user_id, metric_key)
            DO UPDATE SET
                metric_value = model_usage_daily.metric_value + EXCLUDED.metric_value,
                request_count = model_usage_daily.request_count + EXCLUDED.request_count,
                updated_at = NOW()
            """,
            (model_id.strip(), user_id, metric_key.strip(), metric_value, request_count),
        )


def get_usage_summary(database_url: str, *, model_id: str) -> dict[str, Any]:
    with get_connection(database_url) as connection:
        rows = connection.execute(
            """
            SELECT metric_key, SUM(metric_value) AS total_value, SUM(request_count) AS total_requests
            FROM model_usage_daily
            WHERE model_id = %s
            GROUP BY metric_key
            ORDER BY metric_key ASC
            """,
            (model_id.strip(),),
        ).fetchall()
    metrics = {
        str(row["metric_key"]): {
            "value": float(row.get("total_value") or 0),
            "requests": int(row.get("total_requests") or 0),
        }
        for row in rows
    }
    total_requests = sum(item["requests"] for item in metrics.values())
    return {"metrics": metrics, "total_requests": total_requests}


def append_audit_event(
    database_url: str,
    *,
    actor_user_id: int | None,
    event_type: str,
    target_type: str,
    target_id: str,
    payload: dict[str, Any],
) -> None:
    with get_connection(database_url) as connection:
        connection.execute(
            """
            INSERT INTO model_audit_log (actor_user_id, event_type, target_type, target_id, payload, event_hash)
            VALUES (%s, %s, %s, %s, %s::jsonb, decode(repeat('00', 32), 'hex'))
            """,
            (actor_user_id, event_type.strip(), target_type.strip(), target_id.strip(), Jsonb(payload)),
        )
