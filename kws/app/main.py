from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Flask, jsonify, request

app = Flask(__name__)

_DEFAULT_KWS_PORT = 10400
_DEFAULT_HTTP_TIMEOUT_SECONDS = 2.0
_DEFAULT_MAX_RETRIES = 3

_last_emit_by_key: dict[str, float] = {}


def _get_env(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    stripped = value.strip()
    return stripped if stripped else default


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _require_microphone_if_configured() -> None:
    require_mic = _get_bool_env("KWS_REQUIRE_MIC", True)
    if require_mic and not Path("/dev/snd").exists():
        raise RuntimeError("KWS requires /dev/snd, but microphone device path is not available")


def _ensure_model_layout() -> None:
    model_root = Path(_get_env("KWS_MODEL_DIR", "/models/kws"))
    custom_dir = Path(_get_env("KWS_CUSTOM_MODEL_DIR", "/models/kws/custom"))
    preload_model = _get_env("KWS_MODEL_PRELOAD", "")

    if not model_root.exists():
        raise RuntimeError(f"KWS model directory does not exist: {model_root}")
    if not custom_dir.exists():
        raise RuntimeError(f"KWS custom model directory does not exist: {custom_dir}")

    if preload_model:
        candidates = list(model_root.rglob(f"{preload_model}*"))
        if not candidates:
            raise RuntimeError(
                f"KWS preload model '{preload_model}' was not found under model directory {model_root}"
            )


def _post_wake_event_with_retry(payload: dict[str, Any]) -> tuple[bool, str]:
    backend_url = _get_env("KWS_BACKEND_WEBHOOK_URL", "http://backend:5000/voice/wake-events")
    max_retries = max(1, _get_int_env("KWS_WEBHOOK_MAX_RETRIES", _DEFAULT_MAX_RETRIES))
    timeout_seconds = _get_float_env("KWS_WEBHOOK_TIMEOUT_SECONDS", _DEFAULT_HTTP_TIMEOUT_SECONDS)

    request_body = json.dumps(payload).encode("utf-8")

    for attempt in range(max_retries):
        req = Request(
            backend_url,
            data=request_body,
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urlopen(req, timeout=timeout_seconds) as response:
                if 200 <= response.status < 300:
                    return True, "delivered"
                return False, f"backend_http_{response.status}"
        except HTTPError as exc:
            if 400 <= exc.code < 500:
                return False, f"backend_http_{exc.code}"
            if attempt == max_retries - 1:
                return False, f"backend_http_{exc.code}"
        except URLError:
            if attempt == max_retries - 1:
                return False, "backend_unreachable"

        time.sleep(0.25 * (2**attempt))

    return False, "delivery_failed"


@app.get("/health")
def health():
    model_root = Path(_get_env("KWS_MODEL_DIR", "/models/kws"))
    custom_dir = Path(_get_env("KWS_CUSTOM_MODEL_DIR", "/models/kws/custom"))
    return (
        jsonify(
            {
                "status": "ok",
                "service": "kws",
                "engine": "wyoming-openwakeword",
                "model_preload": _get_env("KWS_MODEL_PRELOAD", ""),
                "model_dir_exists": model_root.exists(),
                "custom_model_dir_exists": custom_dir.exists(),
                "microphone_available": Path("/dev/snd").exists(),
            }
        ),
        200,
    )


@app.post("/simulate-detect")
def simulate_detect():
    payload = request.get_json(silent=True) or {}
    wake_word = str(payload.get("wake_word", _get_env("KWS_MODEL_PRELOAD", "default_wake_word"))).strip()
    source_device_id = str(payload.get("source_device_id", "local-mic")).strip()
    event_id = str(payload.get("event_id", "")).strip()

    if not wake_word:
        return jsonify({"queued": False, "reason": "missing_wake_word"}), 400

    try:
        confidence = float(payload.get("confidence", 0.9))
    except (TypeError, ValueError):
        return jsonify({"queued": False, "reason": "invalid_confidence"}), 400

    threshold = _get_float_env("KWS_DETECTION_THRESHOLD", 0.5)
    if confidence < threshold:
        return jsonify({"queued": False, "reason": "below_threshold"}), 202

    now = time.time()
    cooldown_seconds = max(0, _get_int_env("KWS_COOLDOWN_MS", 2000)) / 1000.0
    dedupe_key = f"{source_device_id}:{wake_word}"
    last_sent = _last_emit_by_key.get(dedupe_key)
    if last_sent is not None and (now - last_sent) < cooldown_seconds:
        return jsonify({"queued": False, "reason": "cooldown_active"}), 202
    _last_emit_by_key[dedupe_key] = now

    wake_event: dict[str, Any] = {
        "wake_word": wake_word,
        "confidence": confidence,
        "source_device_id": source_device_id,
        "timestamp_unix": now,
    }
    if event_id:
        wake_event["event_id"] = event_id

    delivered, result = _post_wake_event_with_retry(wake_event)
    status_code = 200 if delivered else 502
    return jsonify({"queued": delivered, "delivery_result": result, "event": wake_event}), status_code


if __name__ == "__main__":
    _require_microphone_if_configured()
    _ensure_model_layout()
    port = _get_int_env("KWS_PORT", _DEFAULT_KWS_PORT)
    app.run(host="0.0.0.0", port=port, debug=True)
