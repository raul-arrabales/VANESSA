# Sandbox

The sandbox service provides isolated Python code execution for agent-driven tasks.

## Responsibilities

- Enforce execution isolation and policy controls
- Provide safe execution APIs for the agent engine
- Prevent direct bypass from frontend/backend paths

## API Surface

- `GET /health`
- `POST /v1/execute`

`POST /v1/execute` is a service-to-service runtime endpoint used through backend and agent-engine governance paths. It accepts Python code plus a small policy envelope, enforces timeout bounds, and returns normalized execution metadata:

- `stdout`
- `stderr`
- `result`
- `error`
- `timed_out`
- `exit_code`

This runtime now acts as the native provider for the optional `sandbox_execution` platform capability. It is not a public browser-facing API.

Canonical service notes: [`sandbox/README.md`](https://github.com/raul-arrabales/VANESSA/blob/main/sandbox/README.md).

> Owner: Sandbox maintainers. Update cadence: whenever execution policy, isolation controls, or API behavior changes.
