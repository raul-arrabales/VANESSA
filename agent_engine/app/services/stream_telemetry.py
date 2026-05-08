from __future__ import annotations

from typing import Any

STREAM_PHASE_RESPONSE_HEADERS = "upstream_response_headers"
STREAM_PHASE_FIRST_TOKEN_DELIVERY = "first_token_delivery"

STREAM_DURATION_MEANING_RESPONSE_HEADERS = "provider queueing, prompt prefill, and first-stream setup"

STREAM_STATUS_LABEL_OPENING = "Opening upstream stream"
STREAM_STATUS_LABEL_SETUP_COMPLETE = "Provider queueing and stream setup complete"
STREAM_STATUS_LABEL_WAITING_FIRST_TOKEN = "Waiting for first token"
STREAM_STATUS_LABEL_RECEIVED_FIRST_TOKEN = "Received first token"
STREAM_STATUS_LABEL_STREAMING = "Streaming response"
STREAM_STATUS_LABEL_STREAMED = "Streamed response"

TRANSPORT_DETAIL_KEYS = (
    "endpoint_host",
    "status_code",
    "duration_ms",
    "duration_meaning",
    "phase",
)


def runtime_llm_binding_telemetry(runtime_snapshot: dict[str, Any]) -> dict[str, Any]:
    capabilities = runtime_snapshot.get("capabilities") if isinstance(runtime_snapshot.get("capabilities"), dict) else {}
    llm_binding = capabilities.get("llm_inference") if isinstance(capabilities.get("llm_inference"), dict) else {}
    deployment_profile = runtime_snapshot.get("deployment_profile") if isinstance(runtime_snapshot.get("deployment_profile"), dict) else {}
    return {
        "provider_slug": llm_binding.get("slug"),
        "provider_key": llm_binding.get("provider_key"),
        "provider_origin": llm_binding.get("provider_origin"),
        "deployment_profile_slug": deployment_profile.get("slug"),
    }
