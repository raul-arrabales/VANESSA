from __future__ import annotations

from json import loads
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


def http_json_ok(url: str, timeout_seconds: float) -> bool:
    req = Request(url, method="GET")
    try:
        with urlopen(req, timeout=timeout_seconds) as response:
            return 200 <= response.status < 300
    except URLError:
        return False


def load_architecture_payload(architecture_json_path: Path) -> dict[str, object]:
    if not architecture_json_path.exists():
        raise FileNotFoundError(str(architecture_json_path))
    raw_payload = architecture_json_path.read_text(encoding="utf-8")
    parsed = loads(raw_payload)
    if not isinstance(parsed, dict):
        raise ValueError("Architecture payload must be a JSON object")
    return parsed


def postgres_ok(database_url: str, get_connection_fn) -> bool:
    try:
        with get_connection_fn(database_url) as connection:
            connection.execute("SELECT 1")
        return True
    except Exception:
        return False
