from __future__ import annotations

from ..services.modelops_cloud_discovery import discover_cloud_provider_models as _discover_cloud_provider_models


def discover_cloud_provider_models(
    database_url: str,
    *,
    config,
    actor_user_id: int,
    actor_role: str,
    provider: str,
    credential_id: str,
):
    return _discover_cloud_provider_models(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        provider=provider,
        credential_id=credential_id,
    )
