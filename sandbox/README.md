# Sandbox

Isolated Python execution service for controlled agent code execution.

Current API:

- `GET /health`
- `POST /v1/execute`

`POST /v1/execute` is a service-to-service runtime endpoint used by backend and agent engine through governed abstractions. It accepts Python code, timeout and policy settings, and returns normalized execution metadata including `stdout`, `stderr`, `result`, `error`, `timed_out`, and `exit_code`.

Inside executed Python code, the incoming payload is exposed as both `input_payload` and `input`.

In the current control-plane model this service acts as the native provider for the optional `sandbox_execution` capability and backs the canonical `tool.python_exec` runtime path.
