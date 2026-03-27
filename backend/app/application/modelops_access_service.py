from __future__ import annotations

from typing import Any

from ..repositories import modelops as modelops_repo
from ..repositories.model_assignments import (
    list_scope_assignments as _list_scope_assignments,
    upsert_scope_assignment as _upsert_scope_assignment,
)
from ..services.modelops_common import ModelOpsError


def require_json_object(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ModelOpsError("invalid_payload", "Expected JSON object", status_code=400)
    return payload


def build_scope_assignment_request(payload: Any) -> dict[str, object]:
    body = require_json_object(payload)
    model_ids = body.get("model_ids")
    if not isinstance(model_ids, list):
        raise ModelOpsError("invalid_model_ids", "model_ids must be an array", status_code=400)
    return {
        "scope": str(body.get("scope", "")).strip().lower(),
        "model_ids": [str(item) for item in model_ids],
    }


def list_scope_assignments(database_url: str):
    return _list_scope_assignments(database_url)


def upsert_scope_assignment(database_url: str, *, scope: str, model_ids: list[str], updated_by_user_id: int):
    try:
        return _upsert_scope_assignment(
            database_url,
            scope=scope,
            model_ids=model_ids,
            updated_by_user_id=updated_by_user_id,
        )
    except ValueError as exc:
        raise ModelOpsError("invalid_scope", "scope must be user, admin, or superadmin", status_code=400) from exc


def append_audit_event(database_url: str, **kwargs) -> None:
    modelops_repo.append_audit_event(database_url, **kwargs)
