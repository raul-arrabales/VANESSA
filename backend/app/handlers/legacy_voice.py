from __future__ import annotations

import os
import time
from typing import Any
from uuid import uuid4

from flask import jsonify, request

from ..services.system_health import http_json_ok

_DEFAULT_COOLDOWN_MS = 2_000
_DEFAULT_DETECTION_THRESHOLD = 0.5
_DEFAULT_HTTP_TIMEOUT_SECONDS = 1.5
_last_wake_by_key: dict[str, float] = {}
_seen_event_ids: dict[str, float] = {}


def _get_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _trim_seen_event_ids(max_age_seconds: float) -> None:
    cutoff = time.time() - max_age_seconds
    stale_ids = [
        event_id for event_id, seen_ts in _seen_event_ids.items() if seen_ts < cutoff
    ]
    for event_id in stale_ids:
        _seen_event_ids.pop(event_id, None)


def wake_events():
    payload = request.get_json(silent=True) or {}

    wake_word = str(payload.get("wake_word", "unknown")).strip() or "unknown"
    source_device_id = str(payload.get("source_device_id", "default")).strip() or "default"
    confidence = payload.get("confidence", 1.0)
    event_id = str(payload.get("event_id", "")).strip()

    try:
        confidence_value = float(confidence)
    except (TypeError, ValueError):
        return jsonify({"accepted": False, "reason": "invalid_confidence"}), 400

    detection_threshold = _get_float_env("KWS_DETECTION_THRESHOLD", _DEFAULT_DETECTION_THRESHOLD)
    if confidence_value < detection_threshold:
        return jsonify({"accepted": False, "reason": "below_threshold"}), 202

    now = time.time()
    cooldown_ms = _get_int_env("KWS_COOLDOWN_MS", _DEFAULT_COOLDOWN_MS)
    cooldown_seconds = max(cooldown_ms, 0) / 1000.0

    if event_id:
        _trim_seen_event_ids(max_age_seconds=max(cooldown_seconds * 2.0, 5.0))
        if event_id in _seen_event_ids:
            return jsonify({"accepted": False, "reason": "duplicate_event_id"}), 202
        _seen_event_ids[event_id] = now

    dedupe_key = f"{source_device_id}:{wake_word}"
    last_seen = _last_wake_by_key.get(dedupe_key)
    if last_seen is not None and (now - last_seen) < cooldown_seconds:
        return jsonify({"accepted": False, "reason": "cooldown_active"}), 202

    _last_wake_by_key[dedupe_key] = now
    session_token = str(uuid4())

    response: dict[str, Any] = {
        "accepted": True,
        "wake_word": wake_word,
        "source_device_id": source_device_id,
        "confidence": confidence_value,
        "session_token": session_token,
        "received_at_unix": now,
    }
    if event_id:
        response["event_id"] = event_id

    return jsonify(response), 200


def voice_health():
    kws_url = os.getenv("KWS_URL", "http://kws:10400").rstrip("/")
    kws_health_url = f"{kws_url}/health"

    return (
        jsonify(
            {
                "status": "ok",
                "service": "backend",
                "voice": {
                    "kws": {
                        "url": kws_url,
                        "reachable": http_json_ok(kws_health_url, timeout_seconds=_DEFAULT_HTTP_TIMEOUT_SECONDS),
                    },
                    "stt": {"configured": False},
                    "tts": {"configured": False},
                },
            }
        ),
        200,
    )
