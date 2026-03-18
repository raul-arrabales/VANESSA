from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp_gateway.app.main import _web_search  # noqa: E402


def test_web_search_returns_normalized_results():
    payload, status_code = _web_search({"query": "hello", "top_k": 2})

    assert status_code == 200
    assert payload["query"] == "hello"
    assert len(payload["results"]) == 2
    assert payload["results"][0]["url"].startswith("https://search.local/")
