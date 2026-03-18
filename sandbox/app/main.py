from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

_MAX_TIMEOUT_SECONDS = 15
_DEFAULT_TIMEOUT_SECONDS = 5
_WRAPPER_CODE = """
import contextlib
import io
import json
import os
from pathlib import Path

SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "print": print,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
}

if os.environ.get("VANESSA_SANDBOX_ALLOW_IMPORTS", "").strip().lower() in {"1", "true", "yes", "on"}:
    SAFE_BUILTINS["__import__"] = __import__

result_path = Path(os.environ["VANESSA_SANDBOX_RESULT_PATH"])
code = os.environ["VANESSA_SANDBOX_CODE"]
input_payload = json.loads(os.environ.get("VANESSA_SANDBOX_INPUT", "null"))
globals_dict = {"__builtins__": SAFE_BUILTINS}
locals_dict = {"input_payload": input_payload, "result": None}

stdout_buffer = io.StringIO()
stderr_buffer = io.StringIO()
error_payload = None
with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
    try:
        exec(code, globals_dict, locals_dict)
    except Exception as exc:
        error_payload = {
            "type": type(exc).__name__,
            "message": str(exc),
        }

result_path.write_text(
    json.dumps(
        {
            "stdout": stdout_buffer.getvalue(),
            "stderr": stderr_buffer.getvalue(),
            "result": locals_dict.get("result"),
            "error": error_payload,
        }
    ),
    encoding="utf-8",
)
"""


def _bool_from_policy(policy: dict[str, Any], key: str, default: bool) -> bool:
    value = policy.get(key, default)
    if isinstance(value, bool):
        return value
    return default


def execute_python(
    *,
    code: str,
    input_payload: Any,
    timeout_seconds: int,
    policy: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    effective_timeout = max(1, min(int(timeout_seconds or _DEFAULT_TIMEOUT_SECONDS), _MAX_TIMEOUT_SECONDS))
    allow_imports = _bool_from_policy(policy, "allow_imports", False)

    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as result_file:
        result_path = Path(result_file.name)

    env = os.environ.copy()
    env["VANESSA_SANDBOX_CODE"] = code
    env["VANESSA_SANDBOX_INPUT"] = json.dumps(input_payload)
    env["VANESSA_SANDBOX_RESULT_PATH"] = str(result_path)
    env["VANESSA_SANDBOX_ALLOW_IMPORTS"] = "true" if allow_imports else "false"

    try:
        completed = subprocess.run(  # noqa: S603
            [sys.executable, "-I", "-c", _WRAPPER_CODE],
            capture_output=True,
            text=True,
            timeout=effective_timeout,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        result_path.unlink(missing_ok=True)
        return {
            "language": "python",
            "stdout": "",
            "stderr": "",
            "result": None,
            "error": {"type": "TimeoutExpired", "message": "Sandbox execution timed out"},
            "exit_code": None,
            "timed_out": True,
        }, 504

    payload: dict[str, Any] = {
        "language": "python",
        "stdout": "",
        "stderr": "",
        "result": None,
        "error": None,
        "exit_code": int(completed.returncode),
        "timed_out": False,
    }
    try:
        raw_result = result_path.read_text(encoding="utf-8")
        parsed = json.loads(raw_result) if raw_result else {}
        if isinstance(parsed, dict):
            payload["stdout"] = str(parsed.get("stdout", ""))
            payload["stderr"] = str(parsed.get("stderr", ""))
            payload["result"] = parsed.get("result")
            payload["error"] = parsed.get("error")
    finally:
        result_path.unlink(missing_ok=True)

    if completed.returncode != 0 and payload["error"] is None:
        payload["error"] = {
            "type": "SandboxProcessError",
            "message": completed.stderr.strip() or completed.stdout.strip() or "Sandbox execution failed",
        }

    status_code = 200 if payload["error"] is None and completed.returncode == 0 else 400
    return payload, status_code


class Handler(BaseHTTPRequestHandler):
    server_version = "VANESSASandbox/0.2"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any] | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "service": "sandbox"})
            return
        self._send_json(404, {"error": "not_found", "message": "Route not found"})

    def do_POST(self) -> None:
        if self.path != "/v1/execute":
            self._send_json(404, {"error": "not_found", "message": "Route not found"})
            return

        payload = self._read_json()
        if payload is None:
            self._send_json(400, {"error": "invalid_payload", "message": "Expected JSON object"})
            return

        language = str(payload.get("language", "python")).strip().lower() or "python"
        if language != "python":
            self._send_json(400, {"error": "unsupported_language", "message": "Only python is supported"})
            return
        code = str(payload.get("code", "")).strip()
        if not code:
            self._send_json(400, {"error": "invalid_code", "message": "code is required"})
            return
        timeout_seconds = payload.get("timeout_seconds", _DEFAULT_TIMEOUT_SECONDS)
        try:
            normalized_timeout = int(timeout_seconds)
        except (TypeError, ValueError):
            self._send_json(400, {"error": "invalid_timeout_seconds", "message": "timeout_seconds must be an integer"})
            return
        if normalized_timeout <= 0:
            self._send_json(400, {"error": "invalid_timeout_seconds", "message": "timeout_seconds must be positive"})
            return
        policy = payload.get("policy", {})
        if policy is None:
            policy = {}
        if not isinstance(policy, dict):
            self._send_json(400, {"error": "invalid_policy", "message": "policy must be an object"})
            return

        result, status_code = execute_python(
            code=code,
            input_payload=payload.get("input"),
            timeout_seconds=normalized_timeout,
            policy=policy,
        )
        self._send_json(status_code, result)


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 6000), Handler)
    server.serve_forever()
