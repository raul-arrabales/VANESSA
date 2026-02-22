# KWS Service

Wake-word service container for VANESSA.

Current implementation scope:

- Exposes `GET /health` for readiness checks.
- Exposes `POST /simulate-detect` to emit wake events to backend webhook.
- Enforces local model directory presence and optional microphone availability.

Environment variables:

- `KWS_PORT` (default `10400`)
- `KWS_MODEL_DIR` (default `/models/kws`)
- `KWS_CUSTOM_MODEL_DIR` (default `/models/kws/custom`)
- `KWS_MODEL_PRELOAD`
- `KWS_BACKEND_WEBHOOK_URL` (default `http://backend:5000/voice/wake-events`)
- `KWS_DETECTION_THRESHOLD` (default `0.5`)
- `KWS_COOLDOWN_MS` (default `2000`)
- `KWS_WEBHOOK_MAX_RETRIES` (default `3`)
- `KWS_WEBHOOK_TIMEOUT_SECONDS` (default `2.0`)
- `KWS_REQUIRE_MIC` (default `true`)
