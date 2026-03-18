from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sandbox.app.main import execute_python  # noqa: E402


def test_execute_python_returns_stdout_and_result():
    payload, status_code = execute_python(
        code="print('hi')\nresult = {'value': 4}",
        input_payload={"name": "Ada"},
        timeout_seconds=5,
        policy={"network_access": False},
    )

    assert status_code == 200
    assert payload["stdout"] == "hi\n"
    assert payload["result"] == {"value": 4}
