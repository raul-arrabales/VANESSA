from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CredentialCreateRequest:
    provider: str
    display_name: str
    api_base_url: str | None
    api_key: str
    credential_scope: str
    owner_user_id: int

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        *,
        current_user_id: int,
        current_role: str,
        allowed_providers: set[str],
    ) -> "CredentialCreateRequest":
        requested_scope = str(payload.get("credential_scope", "personal")).strip().lower() or "personal"
        if requested_scope == "platform" and current_role != "superadmin":
            raise ValueError("forbidden_scope")

        raw_owner_user_id = payload.get("owner_user_id", current_user_id)
        try:
            owner_user_id = int(raw_owner_user_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid_owner_user_id") from exc
        if requested_scope == "personal":
            owner_user_id = current_user_id

        provider = str(payload.get("provider", "openai_compatible")).strip().lower()
        if provider not in allowed_providers:
            raise ValueError("invalid_provider")

        api_key = str(payload.get("api_key", "")).strip()
        if not api_key:
            raise ValueError("invalid_api_key")

        display_name = str(payload.get("display_name", "")).strip() or f"{provider}-key"
        api_base_url = str(payload.get("api_base_url", "")).strip() or None

        return cls(
            provider=provider,
            display_name=display_name,
            api_base_url=api_base_url,
            api_key=api_key,
            credential_scope=requested_scope,
            owner_user_id=owner_user_id,
        )


@dataclass(frozen=True)
class ModelRegisterRequest:
    model_id: str
    name: str
    provider: str
    backend_kind: str
    origin_scope: str
    source_kind: str
    availability: str
    access_scope: str
    provider_model_id: str | None
    credential_id: str | None
    source_id: str | None
    local_path: str | None
    model_size_billion: float | None
    model_type: str | None
    comment: str | None
    metadata: dict[str, Any]

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        *,
        current_role: str,
        allowed_providers: set[str],
    ) -> "ModelRegisterRequest":
        model_id = str(payload.get("id", "")).strip()
        name = str(payload.get("name", "")).strip()
        if not model_id or not name:
            raise ValueError("invalid_model")

        provider = str(payload.get("provider", "openai_compatible")).strip().lower()
        if provider not in allowed_providers:
            raise ValueError("invalid_provider")

        backend_kind = str(payload.get("backend", "external_api")).strip().lower()
        origin_scope = str(payload.get("origin", "personal")).strip().lower()
        if origin_scope == "platform" and current_role != "superadmin":
            raise ValueError("forbidden_origin")

        source_kind = str(payload.get("source", "external_provider" if backend_kind == "external_api" else "local_folder")).strip().lower()
        availability = str(payload.get("availability", "online_only" if backend_kind == "external_api" else "offline_ready")).strip().lower()
        access_scope = str(payload.get("access_scope", "private" if origin_scope == "personal" else "assigned")).strip().lower()
        provider_model_id = str(payload.get("provider_model_id", "")).strip() or None
        credential_id = str(payload.get("credential_id", "")).strip() or None

        if backend_kind == "external_api":
            if not provider_model_id:
                raise ValueError("provider_model_id_required")
            if not credential_id:
                raise ValueError("credential_id_required")

        model_size_raw = payload.get("model_size_billion")
        model_size_billion: float | None = None
        if model_size_raw is not None:
            try:
                model_size_billion = float(model_size_raw)
            except (TypeError, ValueError) as exc:
                raise ValueError("invalid_model_size_billion") from exc

        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}

        return cls(
            model_id=model_id,
            name=name,
            provider=provider,
            backend_kind=backend_kind,
            origin_scope=origin_scope,
            source_kind=source_kind,
            availability=availability,
            access_scope=access_scope,
            provider_model_id=provider_model_id,
            credential_id=credential_id,
            source_id=str(payload.get("source_id", "")).strip() or None,
            local_path=str(payload.get("local_path", "")).strip() or None,
            model_size_billion=model_size_billion,
            model_type=str(payload.get("model_type", "")).strip() or None,
            comment=str(payload.get("comment", "")).strip() or None,
            metadata=metadata,
        )


@dataclass(frozen=True)
class UserModelAssignmentRequest:
    model_id: str
    user_id: int

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "UserModelAssignmentRequest":
        model_id = str(payload.get("model_id", "")).strip()
        if not model_id:
            raise ValueError("invalid_assignment")

        user_id_raw = payload.get("user_id")
        if not isinstance(user_id_raw, int):
            raise ValueError("invalid_assignment")

        return cls(model_id=model_id, user_id=user_id_raw)
