from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..authz import require_role
from ..services.chat_inference import chat_completion_with_allowed_model, coerce_chat_messages, extract_output_text

bp = Blueprint("model_inference_v1", __name__)


def _json_error(status: int, code: str, message: str):
    return jsonify({"error": code, "message": message}), status


@bp.post("/v1/models/generate")
@require_role("user")
def generate_with_allowed_model_v1():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    requested_model_id = str(payload.get("model_id", "")).strip()
    if not requested_model_id:
        return _json_error(400, "invalid_model_id", "model_id is required")

    org_id = str(payload.get("org_id", "")).strip() or None
    group_id = str(payload.get("group_id", "")).strip() or None
    prompt = str(payload.get("prompt", "")).strip()
    history = coerce_chat_messages(payload.get("history", []))
    if prompt:
        history.append({"role": "user", "content": [{"type": "text", "text": prompt}]})

    if not history:
        return _json_error(400, "invalid_input", "history or prompt is required")

    max_tokens_raw = payload.get("max_tokens")
    max_tokens = int(max_tokens_raw) if isinstance(max_tokens_raw, int) and max_tokens_raw > 0 else None
    temperature_raw = payload.get("temperature")
    temperature = float(temperature_raw) if isinstance(temperature_raw, (int, float)) else None

    llm_response, status_code = chat_completion_with_allowed_model(
        requested_model_id=requested_model_id,
        org_id=org_id,
        group_id=group_id,
        messages=history,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    if llm_response is None:
        return _json_error(502, "llm_unreachable", "LLM service unavailable")
    return jsonify(llm_response), status_code


@bp.post("/v1/models/inference")
@require_role("user")
def inference_v1():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(400, "invalid_payload", "Expected JSON object")

    requested_model_id = str(payload.get("model", "")).strip()
    prompt = str(payload.get("prompt", "")).strip()
    if not requested_model_id:
        return _json_error(400, "invalid_model", "model is required")
    if not prompt:
        return _json_error(400, "invalid_prompt", "prompt is required")

    history = coerce_chat_messages(payload.get("history", []))
    history.append({"role": "user", "content": [{"type": "text", "text": prompt}]})

    llm_response, status_code = chat_completion_with_allowed_model(
        requested_model_id=requested_model_id,
        org_id=str(payload.get("org_id", "")).strip() or None,
        group_id=str(payload.get("group_id", "")).strip() or None,
        messages=history,
        max_tokens=None,
        temperature=None,
    )
    if llm_response is None:
        return _json_error(502, "llm_unreachable", "LLM service unavailable")
    if status_code >= 400:
        return jsonify(llm_response), status_code

    return jsonify({"output": extract_output_text(llm_response), "response": llm_response}), 200
