from __future__ import annotations

import time
from typing import Any
from uuid import uuid4


def _m():
    import app.app as backend_app_module

    return backend_app_module


def wake_events():
    m = _m()
    payload = m.request.get_json(silent=True) or {}

    wake_word = str(payload.get("wake_word", "unknown")).strip() or "unknown"
    source_device_id = str(payload.get("source_device_id", "default")).strip() or "default"
    confidence = payload.get("confidence", 1.0)
    event_id = str(payload.get("event_id", "")).strip()

    try:
        confidence_value = float(confidence)
    except (TypeError, ValueError):
        return m.jsonify({"accepted": False, "reason": "invalid_confidence"}), 400

    detection_threshold = m._get_float_env("KWS_DETECTION_THRESHOLD", m._DEFAULT_DETECTION_THRESHOLD)
    if confidence_value < detection_threshold:
        return m.jsonify({"accepted": False, "reason": "below_threshold"}), 202

    now = time.time()
    cooldown_ms = m._get_int_env("KWS_COOLDOWN_MS", m._DEFAULT_COOLDOWN_MS)
    cooldown_seconds = max(cooldown_ms, 0) / 1000.0

    if event_id:
        m._trim_seen_event_ids(max_age_seconds=max(cooldown_seconds * 2.0, 5.0))
        if event_id in m._seen_event_ids:
            return m.jsonify({"accepted": False, "reason": "duplicate_event_id"}), 202
        m._seen_event_ids[event_id] = now

    dedupe_key = f"{source_device_id}:{wake_word}"
    last_seen = m._last_wake_by_key.get(dedupe_key)
    if last_seen is not None and (now - last_seen) < cooldown_seconds:
        return m.jsonify({"accepted": False, "reason": "cooldown_active"}), 202

    m._last_wake_by_key[dedupe_key] = now
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

    return m.jsonify(response), 200


def voice_health():
    m = _m()
    kws_url = m.os.getenv("KWS_URL", "http://kws:10400").rstrip("/")
    kws_health_url = f"{kws_url}/health"

    return (
        m.jsonify(
            {
                "status": "ok",
                "service": "backend",
                "voice": {
                    "kws": {"url": kws_url, "reachable": m._http_json_ok(kws_health_url)},
                    "stt": {"configured": False},
                    "tts": {"configured": False},
                },
            }
        ),
        200,
    )
