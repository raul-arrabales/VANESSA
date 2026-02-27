from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from app.app import app  # noqa: E402


def test_voice_wake_events_accepts_valid_event(monkeypatch):
    app.config.update(TESTING=True)

    monkeypatch.setenv("KWS_DETECTION_THRESHOLD", "0.4")
    monkeypatch.setenv("KWS_COOLDOWN_MS", "0")

    with app.test_client() as client:
        response = client.post(
            "/voice/wake-events",
            json={
                "wake_word": "ok_vanessa",
                "source_device_id": "test-mic",
                "confidence": 0.95,
                "event_id": "evt-1",
            },
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["accepted"] is True
    assert payload["wake_word"] == "ok_vanessa"


def test_voice_health_shape(monkeypatch):
    app.config.update(TESTING=True)
    monkeypatch.setenv("KWS_URL", "http://kws:10400")

    with app.test_client() as client:
        response = client.get("/voice/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["service"] == "backend"
    assert "voice" in payload and "kws" in payload["voice"]
