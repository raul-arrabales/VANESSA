from __future__ import annotations

from typing import Any

from ..services.policy_service import PolicyDeniedError, can_manage_entity
from ..services.registry_service import (
    create_entity_version,
    create_entity_with_version,
    get_entity,
    get_entity_versions,
    list_entities,
)
from ..services.sharing_service import get_shares, grant_share


class RegistryManagementRequestError(ValueError):
    def __init__(self, *, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _require_json_object(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise RegistryManagementRequestError(status_code=400, code="invalid_payload", message="Expected JSON object")
    return payload


def _require_entity(entity_type: str, entity_id: str, *, database_url: str) -> dict[str, Any]:
    entity = get_entity(database_url, entity_type=entity_type, entity_id=entity_id)
    if entity is None:
        raise RegistryManagementRequestError(status_code=404, code="entity_not_found", message="Entity not found")
    return entity


def _validate_non_model_entity_type(entity_type: str) -> str:
    normalized = entity_type.strip().lower()
    if normalized in {"model", "models"}:
        raise RegistryManagementRequestError(status_code=400, code="invalid_entity_type", message="invalid_entity_type")
    return entity_type


def list_registry_entities(database_url: str, *, entity_type: str) -> list[dict[str, Any]]:
    return list_entities(database_url, entity_type=_validate_non_model_entity_type(entity_type))


def get_registry_entity_detail(database_url: str, *, entity_type: str, entity_id: str) -> dict[str, Any]:
    normalized_type = _validate_non_model_entity_type(entity_type)
    entity = _require_entity(normalized_type, entity_id, database_url=database_url)
    return {
        "entity": entity,
        "versions": get_entity_versions(database_url, entity_id=entity_id),
    }


def create_registry_entity_request(
    database_url: str,
    *,
    entity_type: str,
    payload: Any,
    owner_user_id: int,
) -> dict[str, Any]:
    body = _require_json_object(payload)
    entity_id = str(body.get("id", "")).strip()
    version = str(body.get("version", "v1")).strip() or "v1"
    visibility = str(body.get("visibility", "private")).strip().lower() or "private"
    publish = bool(body.get("publish", False))
    spec = body.get("spec") if isinstance(body.get("spec"), dict) else {}
    if not entity_id:
        raise RegistryManagementRequestError(status_code=400, code="invalid_entity_id", message="id is required")

    try:
        return create_entity_with_version(
            database_url,
            entity_type=_validate_non_model_entity_type(entity_type),
            entity_id=entity_id,
            owner_user_id=owner_user_id,
            visibility=visibility,
            spec=spec,
            version=version,
            publish=publish,
        )
    except ValueError as exc:
        raise RegistryManagementRequestError(status_code=400, code="invalid_entity", message=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        text = str(exc)
        if "duplicate" in text.lower() or "unique" in text.lower():
            raise RegistryManagementRequestError(status_code=409, code="duplicate_entity", message="Entity already exists") from exc
        raise RegistryManagementRequestError(status_code=500, code="create_entity_failed", message=text) from exc


def create_registry_entity_version_request(
    database_url: str,
    *,
    entity_type: str,
    entity_id: str,
    payload: Any,
    current_user: dict[str, Any],
) -> dict[str, Any]:
    body = _require_json_object(payload)
    version = str(body.get("version", "")).strip()
    spec = body.get("spec") if isinstance(body.get("spec"), dict) else {}
    publish = bool(body.get("publish", False))
    if not version:
        raise RegistryManagementRequestError(status_code=400, code="invalid_version", message="version is required")

    normalized_type = _validate_non_model_entity_type(entity_type)
    entity = _require_entity(normalized_type, entity_id, database_url=database_url)
    if not can_manage_entity(current_user=current_user, owner_user_id=entity.get("owner_user_id")):
        raise RegistryManagementRequestError(
            status_code=403,
            code="insufficient_role",
            message="Only owner or superadmin can create versions",
        )

    try:
        return create_entity_version(
            database_url,
            entity_type=normalized_type,
            entity_id=entity_id,
            version=version,
            spec=spec,
            publish=publish,
        )
    except LookupError as exc:
        raise RegistryManagementRequestError(status_code=404, code="entity_not_found", message="Entity not found") from exc
    except ValueError as exc:
        raise RegistryManagementRequestError(status_code=400, code="invalid_version_payload", message=str(exc)) from exc


def share_registry_entity_request(
    database_url: str,
    *,
    entity_type: str,
    entity_id: str,
    payload: Any,
    current_user: dict[str, Any],
) -> dict[str, Any]:
    body = _require_json_object(payload)
    entity = _require_entity(_validate_non_model_entity_type(entity_type), entity_id, database_url=database_url)
    grantee_type = str(body.get("grantee_type", "")).strip().lower()
    grantee_id_raw = body.get("grantee_id")
    grantee_id = str(grantee_id_raw).strip() if grantee_id_raw is not None else None
    permission = str(body.get("permission", "view")).strip().lower()
    try:
        return grant_share(
            database_url,
            current_user=current_user,
            entity=entity,
            grantee_type=grantee_type,
            grantee_id=grantee_id,
            permission=permission,
        )
    except PolicyDeniedError as exc:
        raise RegistryManagementRequestError(status_code=403, code="policy_denied", message=str(exc)) from exc
    except ValueError as exc:
        raise RegistryManagementRequestError(status_code=400, code="invalid_share", message=str(exc)) from exc


def list_registry_entity_shares(database_url: str, *, entity_type: str, entity_id: str) -> list[dict[str, Any]]:
    _require_entity(_validate_non_model_entity_type(entity_type), entity_id, database_url=database_url)
    return get_shares(database_url, entity_id=entity_id)


def list_registry_model_entities(database_url: str) -> list[dict[str, Any]]:
    return list_entities(database_url, entity_type="model")


def get_registry_model_detail(database_url: str, *, entity_id: str) -> dict[str, Any]:
    entity = _require_entity("model", entity_id, database_url=database_url)
    return {
        "entity": entity,
        "versions": get_entity_versions(database_url, entity_id=entity_id),
    }


def create_registry_model_request(
    database_url: str,
    *,
    payload: Any,
    owner_user_id: int,
) -> dict[str, Any]:
    body = _require_json_object(payload)
    entity_id = str(body.get("id", "")).strip()
    version = str(body.get("version", "v1")).strip() or "v1"
    visibility = str(body.get("visibility", "private")).strip().lower() or "private"
    publish = bool(body.get("publish", False))
    spec = body.get("spec") if isinstance(body.get("spec"), dict) else {}
    if not entity_id:
        raise RegistryManagementRequestError(status_code=400, code="invalid_entity_id", message="id is required")
    try:
        return create_entity_with_version(
            database_url,
            entity_type="model",
            entity_id=entity_id,
            owner_user_id=owner_user_id,
            visibility=visibility,
            spec=spec,
            version=version,
            publish=publish,
        )
    except ValueError as exc:
        raise RegistryManagementRequestError(status_code=400, code="invalid_entity", message=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        text = str(exc)
        if "duplicate" in text.lower() or "unique" in text.lower():
            raise RegistryManagementRequestError(status_code=409, code="duplicate_entity", message="Entity already exists") from exc
        raise RegistryManagementRequestError(status_code=500, code="create_entity_failed", message=text) from exc


def create_registry_model_version_request(
    database_url: str,
    *,
    entity_id: str,
    payload: Any,
    current_user: dict[str, Any],
) -> dict[str, Any]:
    body = _require_json_object(payload)
    version = str(body.get("version", "")).strip()
    spec = body.get("spec") if isinstance(body.get("spec"), dict) else {}
    publish = bool(body.get("publish", False))
    if not version:
        raise RegistryManagementRequestError(status_code=400, code="invalid_version", message="version is required")
    entity = _require_entity("model", entity_id, database_url=database_url)
    if not can_manage_entity(current_user=current_user, owner_user_id=entity.get("owner_user_id")):
        raise RegistryManagementRequestError(
            status_code=403,
            code="insufficient_role",
            message="Only owner or superadmin can create versions",
        )
    try:
        return create_entity_version(
            database_url,
            entity_type="model",
            entity_id=entity_id,
            version=version,
            spec=spec,
            publish=publish,
        )
    except LookupError as exc:
        raise RegistryManagementRequestError(status_code=404, code="entity_not_found", message="Entity not found") from exc
    except ValueError as exc:
        raise RegistryManagementRequestError(status_code=400, code="invalid_version_payload", message=str(exc)) from exc


def share_registry_model_request(
    database_url: str,
    *,
    entity_id: str,
    payload: Any,
    current_user: dict[str, Any],
) -> dict[str, Any]:
    body = _require_json_object(payload)
    entity = _require_entity("model", entity_id, database_url=database_url)
    grantee_type = str(body.get("grantee_type", "")).strip().lower()
    grantee_id_raw = body.get("grantee_id")
    grantee_id = str(grantee_id_raw).strip() if grantee_id_raw is not None else None
    permission = str(body.get("permission", "view")).strip().lower()
    try:
        return grant_share(
            database_url,
            current_user=current_user,
            entity=entity,
            grantee_type=grantee_type,
            grantee_id=grantee_id,
            permission=permission,
        )
    except PolicyDeniedError as exc:
        raise RegistryManagementRequestError(status_code=403, code="policy_denied", message=str(exc)) from exc
    except ValueError as exc:
        raise RegistryManagementRequestError(status_code=400, code="invalid_share", message=str(exc)) from exc


def list_registry_model_shares(database_url: str, *, entity_id: str) -> list[dict[str, Any]]:
    _require_entity("model", entity_id, database_url=database_url)
    return get_shares(database_url, entity_id=entity_id)
