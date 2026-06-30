from __future__ import annotations

from typing import Any

from vanessa_shared.stream_telemetry import (
    STREAM_DURATION_MEANING_RESPONSE_HEADERS,
    STREAM_PHASE_FIRST_TOKEN_DELIVERY,
    STREAM_PHASE_RESPONSE_HEADERS,
    STREAM_STATUS_LABEL_OPENING,
    STREAM_STATUS_LABEL_RECEIVED_FIRST_TOKEN,
    STREAM_STATUS_LABEL_SETUP_COMPLETE,
    STREAM_STATUS_LABEL_STREAMED,
    STREAM_STATUS_LABEL_STREAMING,
    STREAM_STATUS_LABEL_WAITING_FIRST_TOKEN,
    TRANSPORT_DETAIL_KEYS,
    runtime_llm_binding_telemetry,
)


def llm_binding_telemetry(binding: Any) -> dict[str, Any]:
    return {
        "provider_slug": getattr(binding, "provider_slug", None),
        "provider_key": getattr(binding, "provider_key", None),
        "provider_origin": getattr(binding, "provider_origin", None),
        "deployment_profile_slug": getattr(binding, "deployment_profile_slug", None),
    }
