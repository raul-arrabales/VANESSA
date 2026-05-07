from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..services.runtime_client import LlmRuntimeClientError
from .progress import ProgressRecorder, compact_payload

DeltaEmitter = Callable[[dict[str, Any]], None]


def model_status_details(runtime_snapshot: dict[str, Any], requested_model: str | None) -> dict[str, Any]:
    llm_binding = runtime_snapshot.get("capabilities", {}).get("llm_inference", {})
    deployment_profile = runtime_snapshot.get("deployment_profile", {})
    return {
        "requested_model": requested_model,
        "provider_slug": llm_binding.get("slug"),
        "provider_key": llm_binding.get("provider_key"),
        "deployment_profile_slug": deployment_profile.get("slug"),
    }


def stream_model_completion(
    *,
    client,
    runtime_snapshot: dict[str, Any],
    requested_model: str | None,
    messages: list[dict[str, Any]],
    progress: ProgressRecorder,
    delta_emit: DeltaEmitter,
) -> dict[str, Any]:
    opening_status_id = progress.start(
        kind="opening_stream",
        label="Opening upstream stream",
        details=model_status_details(runtime_snapshot, requested_model),
    )
    waiting_status_id: str | None = None
    streaming_status_id: str | None = None
    output_parts: list[str] = []
    delta_count = 0

    def fail_active(label: str, details: dict[str, Any] | None = None) -> None:
        active_status_id = streaming_status_id or waiting_status_id or opening_status_id
        active_kind = "streaming_tokens" if streaming_status_id else "waiting_first_token" if waiting_status_id else "opening_stream"
        progress.fail(
            active_status_id,
            kind=active_kind,
            label=label,
            details=details or model_status_details(runtime_snapshot, requested_model),
        )

    for event in client.chat_completion_stream(
        requested_model=requested_model,
        messages=messages,
        tools=None,
    ):
        event_type = str(event.get("type", "")).strip().lower()
        if event_type == "transport":
            if waiting_status_id is None:
                progress.complete(
                    opening_status_id,
                    kind="opening_stream",
                    label="Upstream stream connected",
                    details=_stream_transport_details(runtime_snapshot, requested_model, event),
                )
                waiting_status_id = progress.start(
                    kind="waiting_first_token",
                    label="Waiting for first token",
                    details={
                        **_stream_transport_details(runtime_snapshot, requested_model, event),
                        "phase": "provider queueing, prompt prefill, and first-token sampling",
                    },
                )
            continue

        if event_type == "delta":
            text = str(event.get("text", ""))
            if not text:
                continue
            if waiting_status_id is None:
                progress.complete(
                    opening_status_id,
                    kind="opening_stream",
                    label="Upstream stream connected",
                    details=model_status_details(runtime_snapshot, requested_model),
                )
                waiting_status_id = progress.start(
                    kind="waiting_first_token",
                    label="Waiting for first token",
                    details={
                        **model_status_details(runtime_snapshot, requested_model),
                        "phase": "provider queueing, prompt prefill, and first-token sampling",
                    },
                )
            if streaming_status_id is None:
                progress.complete(
                    waiting_status_id,
                    kind="waiting_first_token",
                    label="Received first token",
                    summary="Model started streaming",
                    details=model_status_details(runtime_snapshot, requested_model),
                )
                streaming_status_id = progress.start(
                    kind="streaming_tokens",
                    label="Streaming response",
                    details=model_status_details(runtime_snapshot, requested_model),
                )
            output_parts.append(text)
            delta_count += 1
            delta_emit({"text": text})
            continue

        if event_type == "error":
            payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
            status_code = int(event.get("status_code", 502) or 502)
            fail_active(
                "Response generation failed",
                details={**model_status_details(runtime_snapshot, requested_model), "error": compact_payload(payload)},
            )
            raise LlmRuntimeClientError(
                code=_stream_error_code(status_code),
                message=_stream_error_message(status_code),
                status_code=status_code,
                details=payload,
            )

        if event_type != "complete":
            continue

        response_payload = event.get("response") if isinstance(event.get("response"), dict) else {}
        output_text = _extract_stream_output_text(response_payload) or "".join(output_parts)
        if streaming_status_id is not None:
            progress.complete(
                streaming_status_id,
                kind="streaming_tokens",
                label="Streamed response",
                summary=f"{len(output_text)} characters",
                details={**model_status_details(runtime_snapshot, requested_model), "delta_count": delta_count},
            )
        else:
            progress.complete(
                waiting_status_id or opening_status_id,
                kind="waiting_first_token" if waiting_status_id else "opening_stream",
                label="Received response",
                summary=f"{len(output_text)} characters",
                details={**model_status_details(runtime_snapshot, requested_model), "delta_count": delta_count},
            )
        return {
            "output_text": output_text,
            "tool_calls": [],
            "status_code": int(event.get("status_code", 200) or 200),
            "requested_model": str(event.get("requested_model") or requested_model or "").strip() or requested_model,
        }

    fail_active("Response generation failed")
    raise LlmRuntimeClientError(
        code="runtime_upstream_unavailable",
        message="LLM runtime stream ended before completion",
        status_code=502,
    )


def _stream_error_code(status_code: int) -> str:
    if status_code == 504:
        return "runtime_timeout"
    if status_code >= 502:
        return "runtime_upstream_unavailable"
    return "runtime_request_failed"


def _stream_error_message(status_code: int) -> str:
    if status_code == 504:
        return "LLM runtime stream timed out"
    if status_code >= 502:
        return "LLM runtime stream unavailable"
    return "LLM runtime stream failed"


def _extract_stream_output_text(response_payload: dict[str, Any]) -> str:
    output = response_payload.get("output")
    if isinstance(output, list):
        text_parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                if str(part.get("type", "")).strip().lower() != "text":
                    continue
                text = str(part.get("text", "")).strip()
                if text:
                    text_parts.append(text)
        return "\n".join(text_parts)

    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    return content.strip() if isinstance(content, str) else ""


def _stream_transport_details(
    runtime_snapshot: dict[str, Any],
    requested_model: str | None,
    event: dict[str, Any] | None = None,
) -> dict[str, Any]:
    details = model_status_details(runtime_snapshot, requested_model)
    if not event:
        return details
    for key in ("endpoint_host", "status_code", "duration_ms"):
        if event.get(key) is not None:
            details[key] = event.get(key)
    return details
