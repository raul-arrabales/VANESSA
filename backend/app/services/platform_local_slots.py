from __future__ import annotations

import logging
from typing import Any

from ..config import AuthConfig
from ..repositories.modelops import get_model as get_model_by_id
from ..repositories import platform_control_plane as platform_repo
from .platform_service_types import (
    LocalModelSlotState,
    ProviderRow,
    _CLOUD_PROVIDER_KEYS,
    _LOCAL_SLOT_CONFIG_KEYS,
    _LOCAL_SLOT_STATE_EMPTY,
    _LOCAL_SLOT_STATE_ERROR,
    _LOCAL_SLOT_STATE_LOADED,
    _LOCAL_SLOT_STATE_LOADING,
    _LOCAL_SLOT_STATE_RECONCILING,
    _MODEL_BEARING_CAPABILITIES,
)
from .platform_shared import _expected_task_key, _runtime_model_entries_for_capability
from .platform_types import CAPABILITY_LLM_INFERENCE, PlatformControlPlaneError, ProviderBinding
from .platform_adapters import http_json_request

logger = logging.getLogger(__name__)


def _normalized_optional_slot_string(value: Any) -> str | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    if normalized.lower() in {"none", "null"}:
        return None
    return normalized


def _local_slot_payload_from_config(config: dict[str, Any]) -> LocalModelSlotState:
    loaded_managed_model_id = _normalized_optional_slot_string(config.get("loaded_managed_model_id"))
    loaded_managed_model_name = _normalized_optional_slot_string(config.get("loaded_managed_model_name"))
    loaded_runtime_model_id = _normalized_optional_slot_string(config.get("loaded_runtime_model_id"))
    loaded_local_path = _normalized_optional_slot_string(config.get("loaded_local_path"))
    loaded_source_id = _normalized_optional_slot_string(config.get("loaded_source_id"))
    load_error = _normalized_optional_slot_string(config.get("load_error"))
    raw_state = str(config.get("load_state") or "").strip().lower()
    if loaded_managed_model_id:
        load_state = raw_state or _LOCAL_SLOT_STATE_RECONCILING
    elif raw_state == _LOCAL_SLOT_STATE_ERROR:
        load_state = _LOCAL_SLOT_STATE_ERROR
    else:
        load_state = _LOCAL_SLOT_STATE_EMPTY
    return {
        "loaded_managed_model_id": loaded_managed_model_id,
        "loaded_managed_model_name": loaded_managed_model_name,
        "loaded_runtime_model_id": loaded_runtime_model_id,
        "loaded_local_path": loaded_local_path,
        "loaded_source_id": loaded_source_id,
        "load_state": load_state,
        "load_error": load_error,
    }


def _config_with_local_slot(
    config: dict[str, Any],
    *,
    loaded_managed_model_id: str | None,
    loaded_managed_model_name: str | None,
    loaded_runtime_model_id: str | None,
    loaded_local_path: str | None,
    loaded_source_id: str | None,
    load_state: str,
    load_error: str | None = None,
) -> dict[str, Any]:
    updated = {
        key: value
        for key, value in dict(config).items()
        if key not in _LOCAL_SLOT_CONFIG_KEYS
    }
    if loaded_managed_model_id:
        updated["loaded_managed_model_id"] = loaded_managed_model_id
    if loaded_managed_model_name:
        updated["loaded_managed_model_name"] = loaded_managed_model_name
    if loaded_runtime_model_id:
        updated["loaded_runtime_model_id"] = loaded_runtime_model_id
    if loaded_local_path:
        updated["loaded_local_path"] = loaded_local_path
    if loaded_source_id:
        updated["loaded_source_id"] = loaded_source_id
    updated["load_state"] = load_state
    if load_error:
        updated["load_error"] = load_error
    return updated


def _is_local_model_slot_provider(row: dict[str, Any]) -> bool:
    capability_key = str(row.get("capability_key") or "").strip().lower()
    provider_key = str(row.get("provider_key") or "").strip().lower()
    return capability_key in _MODEL_BEARING_CAPABILITIES and provider_key not in _CLOUD_PROVIDER_KEYS


def _hydrate_provider_row_for_local_slot(
    database_url: str,
    *,
    provider_row: ProviderRow,
) -> ProviderRow:
    if not isinstance(provider_row, dict):
        return provider_row
    capability_key = str(provider_row.get("capability_key") or "").strip().lower()
    adapter_kind = str(provider_row.get("adapter_kind") or "").strip().lower()
    if capability_key and adapter_kind:
        return provider_row
    provider_instance_id = str(provider_row.get("id") or "").strip()
    if not provider_instance_id:
        return provider_row
    hydrated = platform_repo.get_provider_instance(database_url, provider_instance_id)
    return hydrated if isinstance(hydrated, dict) else provider_row


def _runtime_admin_base_url(provider_row: dict[str, Any]) -> str | None:
    config = provider_row.get("config_json") if isinstance(provider_row.get("config_json"), dict) else {}
    runtime_admin_base_url = str(config.get("runtime_admin_base_url") or "").strip()
    if runtime_admin_base_url:
        return runtime_admin_base_url.rstrip("/")
    runtime_base_url = str(config.get("runtime_base_url") or "").strip()
    if runtime_base_url:
        return runtime_base_url.rstrip("/").removesuffix("/v1")
    return None


def _runtime_admin_state(provider_row: dict[str, Any]) -> tuple[dict[str, Any] | None, int]:
    runtime_admin_base_url = _runtime_admin_base_url(provider_row)
    if not runtime_admin_base_url:
        return None, 404
    payload, status_code = http_json_request(
        f"{runtime_admin_base_url}/v1/admin/runtime-state",
        method="GET",
        timeout_seconds=5.0,
    )
    if isinstance(payload, dict) and isinstance(payload.get("detail"), dict):
        detail = payload.get("detail")
        return dict(detail), status_code
    return (dict(payload) if isinstance(payload, dict) else None), status_code


def _runtime_admin_load_model(
    provider_row: dict[str, Any],
    *,
    runtime_model_id: str,
    local_path: str,
    managed_model_id: str,
    display_name: str,
) -> tuple[dict[str, Any] | None, int]:
    runtime_admin_base_url = _runtime_admin_base_url(provider_row)
    if not runtime_admin_base_url:
        return None, 404
    payload, status_code = http_json_request(
        f"{runtime_admin_base_url}/v1/admin/load-model",
        method="POST",
        payload={
            "runtime_model_id": runtime_model_id,
            "local_path": local_path,
            "managed_model_id": managed_model_id,
            "display_name": display_name,
        },
        timeout_seconds=8.0,
    )
    if isinstance(payload, dict) and isinstance(payload.get("detail"), dict):
        detail = payload.get("detail")
        return dict(detail), status_code
    return (dict(payload) if isinstance(payload, dict) else None), status_code


def _runtime_admin_unload_model(provider_row: dict[str, Any]) -> tuple[dict[str, Any] | None, int]:
    runtime_admin_base_url = _runtime_admin_base_url(provider_row)
    if not runtime_admin_base_url:
        return None, 404
    payload, status_code = http_json_request(
        f"{runtime_admin_base_url}/v1/admin/unload-model",
        method="POST",
        timeout_seconds=8.0,
    )
    if isinstance(payload, dict) and isinstance(payload.get("detail"), dict):
        detail = payload.get("detail")
        return dict(detail), status_code
    return (dict(payload) if isinstance(payload, dict) else None), status_code


def _local_slot_with_runtime_state(
    slot: dict[str, Any],
    runtime_state: dict[str, Any] | None,
    status_code: int,
) -> dict[str, Any]:
    resolved = dict(slot)
    if not isinstance(runtime_state, dict):
        if resolved.get("loaded_managed_model_id"):
            resolved["load_state"] = _LOCAL_SLOT_STATE_ERROR
            if not resolved.get("load_error"):
                resolved["load_error"] = f"runtime_state_unavailable:{status_code}"
        return resolved
    managed_model_id = _normalized_optional_slot_string(runtime_state.get("managed_model_id"))
    display_name = _normalized_optional_slot_string(runtime_state.get("display_name"))
    runtime_model_id = _normalized_optional_slot_string(runtime_state.get("runtime_model_id"))
    local_path = _normalized_optional_slot_string(runtime_state.get("local_path"))
    last_error = _normalized_optional_slot_string(runtime_state.get("last_error"))
    raw_state = str(runtime_state.get("load_state") or "").strip().lower()
    if managed_model_id and not resolved.get("loaded_managed_model_id"):
        resolved["loaded_managed_model_id"] = managed_model_id
    if display_name and not resolved.get("loaded_managed_model_name"):
        resolved["loaded_managed_model_name"] = display_name
    if runtime_model_id:
        resolved["loaded_runtime_model_id"] = runtime_model_id
    if local_path:
        resolved["loaded_local_path"] = local_path
    if raw_state in {
        _LOCAL_SLOT_STATE_EMPTY,
        _LOCAL_SLOT_STATE_LOADING,
        _LOCAL_SLOT_STATE_RECONCILING,
        _LOCAL_SLOT_STATE_LOADED,
        _LOCAL_SLOT_STATE_ERROR,
    }:
        resolved["load_state"] = raw_state
    if last_error:
        resolved["load_error"] = last_error
    elif resolved.get("load_state") == _LOCAL_SLOT_STATE_LOADED:
        resolved["load_error"] = None
    return resolved


def _update_provider_local_slot(
    database_url: str,
    *,
    provider_row: dict[str, Any],
    config_json: dict[str, Any],
) -> dict[str, Any]:
    updated = platform_repo.update_provider_instance(
        database_url,
        provider_instance_id=str(provider_row.get("id") or "").strip(),
        slug=str(provider_row.get("slug") or "").strip(),
        display_name=str(provider_row.get("display_name") or "").strip(),
        description=str(provider_row.get("description") or "").strip(),
        endpoint_url=str(provider_row.get("endpoint_url") or "").strip(),
        healthcheck_url=str(provider_row.get("healthcheck_url") or "").strip() or None,
        enabled=bool(provider_row.get("enabled")),
        config_json=config_json,
    )
    if updated is None:
        raise PlatformControlPlaneError("provider_not_found", "Provider instance not found", status_code=404)
    return updated


def _provider_runtime_inventory(provider_row: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    if not _is_local_model_slot_provider(provider_row):
        return [], 200
    from .platform_bindings import _adapter_from_binding

    binding = ProviderBinding.from_row(provider_row)
    try:
        adapter = _adapter_from_binding(binding)
    except PlatformControlPlaneError:
        return [], 500
    list_models = getattr(adapter, "list_models", None)
    if not callable(list_models):
        return [], 200
    try:
        payload, status_code = list_models()
    except PlatformControlPlaneError:
        return [], 502
    return _runtime_model_entries_for_capability(binding.capability_key, payload), status_code


def _effective_local_slot(provider_row: dict[str, Any]) -> dict[str, Any]:
    config = dict(provider_row.get("config_json") or {})
    slot = _local_slot_payload_from_config(config)
    if not _is_local_model_slot_provider(provider_row):
        return slot
    runtime_state, runtime_status = _runtime_admin_state(provider_row)
    if runtime_state is not None:
        slot = _local_slot_with_runtime_state(slot, runtime_state, runtime_status)
    runtime_items, status_code = _provider_runtime_inventory(provider_row)
    loaded_runtime_model_id = str(slot.get("loaded_runtime_model_id") or "").strip()
    if not loaded_runtime_model_id:
        return slot
    available_ids = {
        str(item.get("id") or "").strip()
        for item in runtime_items
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    if loaded_runtime_model_id in available_ids:
        slot["load_state"] = _LOCAL_SLOT_STATE_LOADED
        slot["load_error"] = None
        return slot
    if slot.get("load_state") == _LOCAL_SLOT_STATE_LOADING:
        return slot
    if 200 <= status_code < 300:
        slot["load_state"] = _LOCAL_SLOT_STATE_RECONCILING
        return slot
    slot["load_state"] = _LOCAL_SLOT_STATE_ERROR
    if not slot.get("load_error"):
        slot["load_error"] = f"runtime_inventory_unavailable:{status_code}"
    return slot


def _slot_config_from_state(config: dict[str, Any], slot: dict[str, Any]) -> dict[str, Any]:
    return _config_with_local_slot(
        config,
        loaded_managed_model_id=_normalized_optional_slot_string(slot.get("loaded_managed_model_id")),
        loaded_managed_model_name=_normalized_optional_slot_string(slot.get("loaded_managed_model_name")),
        loaded_runtime_model_id=_normalized_optional_slot_string(slot.get("loaded_runtime_model_id")),
        loaded_local_path=_normalized_optional_slot_string(slot.get("loaded_local_path")),
        loaded_source_id=_normalized_optional_slot_string(slot.get("loaded_source_id")),
        load_state=str(slot.get("load_state") or _LOCAL_SLOT_STATE_EMPTY).strip().lower() or _LOCAL_SLOT_STATE_EMPTY,
        load_error=_normalized_optional_slot_string(slot.get("load_error")),
    )


def inspect_provider_local_slot_runtime(
    database_url: str,
    *,
    provider_row: ProviderRow,
) -> dict[str, Any]:
    hydrated_provider_row = _hydrate_provider_row_for_local_slot(database_url, provider_row=provider_row)
    config = dict(hydrated_provider_row.get("config_json") or {}) if isinstance(hydrated_provider_row, dict) else {}
    slot = _local_slot_payload_from_config(config)
    runtime_model_id = _normalized_optional_slot_string(slot.get("loaded_runtime_model_id")) or _normalized_optional_slot_string(
        slot.get("loaded_local_path")
    )
    has_persisted_intent = bool(
        slot.get("loaded_managed_model_id")
        and runtime_model_id
        and _normalized_optional_slot_string(slot.get("loaded_local_path"))
    )
    if not isinstance(hydrated_provider_row, dict) or not _is_local_model_slot_provider(hydrated_provider_row):
        return {
            "provider_row": hydrated_provider_row,
            "slot": slot,
            "runtime_model_id": runtime_model_id,
            "has_persisted_intent": has_persisted_intent,
            "runtime_state": None,
            "runtime_state_status_code": 404,
            "runtime_inventory": [],
            "runtime_inventory_status_code": 404,
            "runtime_inventory_ids": [],
            "runtime_empty": False,
            "target_available": False,
            "is_drifted": False,
        }

    runtime_state, runtime_state_status_code = _runtime_admin_state(hydrated_provider_row)
    runtime_inventory, runtime_inventory_status_code = _provider_runtime_inventory(hydrated_provider_row)
    runtime_inventory_ids = [
        str(item.get("id") or "").strip()
        for item in runtime_inventory
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]
    runtime_empty = 200 <= runtime_inventory_status_code < 300 and not runtime_inventory_ids
    target_available = bool(runtime_model_id and runtime_model_id in set(runtime_inventory_ids))
    runtime_state_load_state = (
        str(runtime_state.get("load_state") or "").strip().lower()
        if isinstance(runtime_state, dict)
        else ""
    )
    is_drifted = bool(
        has_persisted_intent
        and (
            runtime_empty
            or (runtime_model_id and runtime_inventory_ids and not target_available)
            or runtime_state_load_state in {_LOCAL_SLOT_STATE_EMPTY, _LOCAL_SLOT_STATE_ERROR}
        )
    )
    return {
        "provider_row": hydrated_provider_row,
        "slot": slot,
        "runtime_model_id": runtime_model_id,
        "has_persisted_intent": has_persisted_intent,
        "runtime_state": runtime_state,
        "runtime_state_status_code": runtime_state_status_code,
        "runtime_inventory": runtime_inventory,
        "runtime_inventory_status_code": runtime_inventory_status_code,
        "runtime_inventory_ids": runtime_inventory_ids,
        "runtime_empty": runtime_empty,
        "target_available": target_available,
        "is_drifted": is_drifted,
    }


def recover_provider_local_slot_runtime(
    database_url: str,
    *,
    provider_row: ProviderRow,
    force: bool = False,
) -> tuple[ProviderRow, bool, dict[str, Any]]:
    inspection = inspect_provider_local_slot_runtime(database_url, provider_row=provider_row)
    hydrated_provider_row = inspection["provider_row"]
    if not isinstance(hydrated_provider_row, dict) or not _is_local_model_slot_provider(hydrated_provider_row):
        return hydrated_provider_row, False, inspection
    should_reconcile = bool(
        inspection["has_persisted_intent"]
        and (inspection["is_drifted"] or (force and not inspection["target_available"]))
    )
    if not should_reconcile:
        return hydrated_provider_row, False, inspection
    reconciled = reconcile_provider_local_slot(
        database_url,
        provider_row=hydrated_provider_row,
    )
    refreshed_inspection = inspect_provider_local_slot_runtime(database_url, provider_row=reconciled)
    return refreshed_inspection["provider_row"], True, refreshed_inspection


def reconcile_provider_local_slot(
    database_url: str,
    *,
    provider_row: ProviderRow,
) -> ProviderRow:
    provider_row = _hydrate_provider_row_for_local_slot(database_url, provider_row=provider_row)
    if not _is_local_model_slot_provider(provider_row):
        return provider_row

    provider_config = dict(provider_row.get("config_json") or {})
    slot = _local_slot_payload_from_config(provider_config)
    managed_model_id = _normalized_optional_slot_string(slot.get("loaded_managed_model_id"))
    local_path = _normalized_optional_slot_string(slot.get("loaded_local_path"))
    runtime_model_id = _normalized_optional_slot_string(slot.get("loaded_runtime_model_id")) or local_path
    display_name = _normalized_optional_slot_string(slot.get("loaded_managed_model_name"))

    runtime_state, runtime_status = _runtime_admin_state(provider_row)
    resolved_slot = _local_slot_with_runtime_state(slot, runtime_state, runtime_status)

    runtime_state_model_id = (
        _normalized_optional_slot_string(runtime_state.get("runtime_model_id"))
        if isinstance(runtime_state, dict)
        else None
    )
    runtime_load_state = (
        str(runtime_state.get("load_state") or "").strip().lower()
        if isinstance(runtime_state, dict)
        else ""
    )
    runtime_aligned = (
        runtime_model_id is not None
        and runtime_state_model_id == runtime_model_id
        and runtime_load_state in {
            _LOCAL_SLOT_STATE_LOADING,
            _LOCAL_SLOT_STATE_RECONCILING,
            _LOCAL_SLOT_STATE_LOADED,
        }
    )

    if managed_model_id and runtime_model_id and local_path and not runtime_aligned:
        logger.info(
            "Reconciling local provider slot for %s (%s): requesting runtime load for managed_model_id=%s runtime_model_id=%s",
            str(provider_row.get("slug") or "").strip() or str(provider_row.get("id") or "").strip(),
            str(provider_row.get("provider_key") or "").strip(),
            managed_model_id,
            runtime_model_id,
        )
        runtime_state, runtime_status = _runtime_admin_load_model(
            provider_row,
            runtime_model_id=runtime_model_id,
            local_path=local_path,
            managed_model_id=managed_model_id,
            display_name=display_name or managed_model_id,
        )
        if runtime_status >= 400 and not (runtime_status == 404 and runtime_state is None):
            logger.warning(
                "Local provider slot reconciliation failed for %s (%s): status=%s message=%s",
                str(provider_row.get("slug") or "").strip() or str(provider_row.get("id") or "").strip(),
                str(provider_row.get("provider_key") or "").strip(),
                runtime_status,
                str((runtime_state or {}).get("message") or f"runtime_load_failed:{runtime_status}"),
            )
            resolved_slot = {
                **resolved_slot,
                "load_state": _LOCAL_SLOT_STATE_ERROR,
                "load_error": str((runtime_state or {}).get("message") or f"runtime_load_failed:{runtime_status}"),
            }
        elif isinstance(runtime_state, dict):
            resolved_slot = _local_slot_with_runtime_state(slot, runtime_state, runtime_status)

    updated_config = _slot_config_from_state(provider_config, resolved_slot)
    if updated_config == provider_config:
        return provider_row

    return _update_provider_local_slot(
        database_url,
        provider_row=provider_row,
        config_json=updated_config,
    )


def reconcile_local_provider_slots(
    database_url: str,
    *,
    provider_rows: list[ProviderRow],
) -> list[ProviderRow]:
    reconciled: list[ProviderRow] = []
    for provider_row in provider_rows:
        if not isinstance(provider_row, dict):
            continue
        reconciled.append(
            reconcile_provider_local_slot(
                database_url,
                provider_row=provider_row,
            )
        )
    return reconciled


def assign_provider_loaded_model(
    database_url: str,
    *,
    provider_row: ProviderRow,
    managed_model_id: str,
) -> ProviderRow:
    normalized_model_id = managed_model_id.strip()
    if not normalized_model_id:
        raise PlatformControlPlaneError("managed_model_required", "managed_model_id is required", status_code=400)
    if not _is_local_model_slot_provider(provider_row):
        raise PlatformControlPlaneError(
            "provider_slot_unsupported",
            "Only local LLM and embeddings providers support loaded-model slots",
            status_code=409,
        )
    model_row = get_model_by_id(database_url, normalized_model_id)
    if model_row is None:
        raise PlatformControlPlaneError("managed_model_not_found", "Managed model not found", status_code=404)

    capability_key = str(provider_row.get("capability_key") or "").strip().lower()
    expected_task_key = _expected_task_key(capability_key)
    task_key = str(model_row.get("task_key") or "").strip().lower()
    if task_key != expected_task_key:
        raise PlatformControlPlaneError(
            "managed_model_task_mismatch",
            f"Provider requires a model with task_key={expected_task_key}",
            status_code=409,
            details={"provider_instance_id": provider_row.get("id"), "managed_model_id": normalized_model_id},
        )
    if str(model_row.get("backend_kind") or "").strip().lower() != "local":
        raise PlatformControlPlaneError(
            "managed_model_backend_mismatch",
            "Local provider slots only support local managed models",
            status_code=409,
            details={"provider_instance_id": provider_row.get("id"), "managed_model_id": normalized_model_id},
        )

    from .platform_serialization import _runtime_model_identifier, _serialize_provider_row

    runtime_model_id = _runtime_model_identifier(model_row)
    if not runtime_model_id:
        raise PlatformControlPlaneError(
            "provider_resource_id_required",
            "Selected local model must define a runtime identifier",
            status_code=400,
            details={"managed_model_id": normalized_model_id},
        )

    provider_config = dict(provider_row.get("config_json") or {})
    updated_config = _config_with_local_slot(
        provider_config,
        loaded_managed_model_id=normalized_model_id,
        loaded_managed_model_name=str(model_row.get("name") or normalized_model_id).strip() or normalized_model_id,
        loaded_runtime_model_id=runtime_model_id,
        loaded_local_path=str(model_row.get("local_path") or "").strip() or None,
        loaded_source_id=str(model_row.get("source_id") or "").strip() or None,
        load_state=_LOCAL_SLOT_STATE_LOADING,
        load_error=None,
    )

    updated = _update_provider_local_slot(
        database_url,
        provider_row=provider_row,
        config_json=updated_config,
    )
    runtime_state, status_code = _runtime_admin_load_model(
        {**provider_row, "config_json": updated_config},
        runtime_model_id=runtime_model_id,
        local_path=str(model_row.get("local_path") or "").strip(),
        managed_model_id=normalized_model_id,
        display_name=str(model_row.get("name") or normalized_model_id).strip() or normalized_model_id,
    )
    if status_code >= 400 and not (status_code == 404 and runtime_state is None):
        errored_config = _config_with_local_slot(
            updated_config,
            loaded_managed_model_id=normalized_model_id,
            loaded_managed_model_name=str(model_row.get("name") or normalized_model_id).strip() or normalized_model_id,
            loaded_runtime_model_id=runtime_model_id,
            loaded_local_path=str(model_row.get("local_path") or "").strip() or None,
            loaded_source_id=str(model_row.get("source_id") or "").strip() or None,
            load_state=_LOCAL_SLOT_STATE_ERROR,
            load_error=str((runtime_state or {}).get("message") or f"runtime_load_failed:{status_code}"),
        )
        updated = _update_provider_local_slot(
            database_url,
            provider_row={**provider_row, **updated},
            config_json=errored_config,
        )
    elif isinstance(runtime_state, dict):
        updated = _update_provider_local_slot(
            database_url,
            provider_row={**provider_row, **updated},
            config_json=_config_with_local_slot(
                updated_config,
                loaded_managed_model_id=normalized_model_id,
                loaded_managed_model_name=str(model_row.get("name") or normalized_model_id).strip() or normalized_model_id,
                loaded_runtime_model_id=str(runtime_state.get("runtime_model_id") or runtime_model_id).strip() or runtime_model_id,
                loaded_local_path=str(runtime_state.get("local_path") or model_row.get("local_path") or "").strip() or None,
                loaded_source_id=str(model_row.get("source_id") or "").strip() or None,
                load_state=str(runtime_state.get("load_state") or _LOCAL_SLOT_STATE_LOADING).strip().lower()
                or _LOCAL_SLOT_STATE_LOADING,
                load_error=str(runtime_state.get("last_error") or "").strip() or None,
            ),
        )
    return _serialize_provider_row({**(platform_repo.get_provider_instance(database_url, str(provider_row["id"])) or {}), **updated})


def clear_provider_loaded_model(
    database_url: str,
    *,
    provider_row: ProviderRow,
) -> ProviderRow:
    if not _is_local_model_slot_provider(provider_row):
        raise PlatformControlPlaneError(
            "provider_slot_unsupported",
            "Only local LLM and embeddings providers support loaded-model slots",
            status_code=409,
        )
    from .platform_serialization import _serialize_provider_row

    provider_config = dict(provider_row.get("config_json") or {})
    cleared_config = _config_with_local_slot(
        provider_config,
        loaded_managed_model_id=None,
        loaded_managed_model_name=None,
        loaded_runtime_model_id=None,
        loaded_local_path=None,
        loaded_source_id=None,
        load_state=_LOCAL_SLOT_STATE_EMPTY,
        load_error=None,
    )
    updated = _update_provider_local_slot(
        database_url,
        provider_row=provider_row,
        config_json=cleared_config,
    )
    runtime_state, status_code = _runtime_admin_unload_model({**provider_row, "config_json": cleared_config})
    if status_code >= 400 and not (status_code == 404 and runtime_state is None):
        updated = _update_provider_local_slot(
            database_url,
            provider_row={**provider_row, **updated},
            config_json=_config_with_local_slot(
                provider_config,
                loaded_managed_model_id=None,
                loaded_managed_model_name=None,
                loaded_runtime_model_id=None,
                loaded_local_path=None,
                loaded_source_id=None,
                load_state=_LOCAL_SLOT_STATE_ERROR,
                load_error=str((runtime_state or {}).get("message") or f"runtime_unload_failed:{status_code}"),
            ),
        )
    return _serialize_provider_row({**(platform_repo.get_provider_instance(database_url, str(provider_row["id"])) or {}), **updated})
