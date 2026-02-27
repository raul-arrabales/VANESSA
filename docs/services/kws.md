# KWS Service

The wake-word service handles offline wake detection and emits wake events to backend webhook endpoints.

## Responsibilities

- Wake-word model checks and loading
- Health endpoint for readiness
- Simulation endpoint for local testing
- Controlled webhook delivery to backend

## Current Endpoints

- `GET /health`
- `POST /simulate-detect`

Canonical service notes: [`kws/README.md`](https://github.com/raul-arrabales/VANESSA/blob/main/kws/README.md).

> Owner: KWS maintainers. Update cadence: whenever wake-event schema, model loading rules, or webhook behavior changes.
