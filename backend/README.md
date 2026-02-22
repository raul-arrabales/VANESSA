# Backend (Flask API)

HTTP entrypoint for frontend and orchestration gateway.

Current voice-related endpoints:

- `POST /voice/wake-events` accepts wake detection events from `kws`.
- `GET /voice/health` reports voice service integration health status.
