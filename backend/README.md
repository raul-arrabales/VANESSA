# Backend (Flask API)

HTTP entrypoint for frontend and orchestration gateway.

Current voice-related endpoints:

- `POST /voice/wake-events` accepts wake detection events from `kws`.
- `GET /voice/health` reports voice service integration health status.

System diagnostics endpoints:

- `GET /system/health` returns aggregate reachability for core services.
- `GET /system/architecture` returns generated architecture graph JSON.
- `GET /system/architecture.svg` returns generated architecture diagram SVG.
