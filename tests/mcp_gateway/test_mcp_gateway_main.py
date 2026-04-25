from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp_gateway.app import main as mcp_main  # noqa: E402


def test_web_search_returns_normalized_searxng_results(monkeypatch):
    seen: dict[str, object] = {}

    def fake_fetch_json(url: str, *, timeout_seconds: float):
        seen["url"] = url
        seen["timeout_seconds"] = timeout_seconds
        return {
            "results": [
                {
                    "title": "Example One",
                    "url": "https://example.com/one",
                    "content": "First result",
                    "engine": "duckduckgo",
                },
                {
                    "title": "Duplicate",
                    "url": "https://example.com/one",
                    "content": "Duplicate result",
                    "engine": "bing",
                },
                {
                    "title": "Example Two",
                    "url": "https://example.com/two",
                    "content": "Second result",
                    "engines": ["brave", "google"],
                },
            ]
        }, 200

    monkeypatch.setenv("SEARXNG_URL", "http://searxng.local")
    monkeypatch.setenv("SEARXNG_TIMEOUT_SECONDS", "4")
    monkeypatch.setattr(mcp_main, "_fetch_json", fake_fetch_json)

    payload, status_code = mcp_main._web_search(
        {
            "query": "hello world",
            "top_k": 3,
            "language": "en",
            "time_range": "day",
            "safesearch": 2,
            "categories": "general,news",
        }
    )

    assert status_code == 200
    assert payload["query"] == "hello world"
    assert len(payload["results"]) == 2
    assert payload["results"][0] == {
        "title": "Example One",
        "url": "https://example.com/one",
        "snippet": "First result",
        "engine": "duckduckgo",
        "rank": 1,
    }
    assert payload["results"][1]["engine"] == "brave, google"
    assert seen["timeout_seconds"] == 4.0

    parsed = urlparse(str(seen["url"]))
    query = parse_qs(parsed.query)
    assert parsed.geturl().startswith("http://searxng.local/search?")
    assert query["q"] == ["hello world"]
    assert query["format"] == ["json"]
    assert query["language"] == ["en"]
    assert query["time_range"] == ["day"]
    assert query["safesearch"] == ["2"]
    assert query["categories"] == ["general,news"]


def test_web_search_returns_empty_results(monkeypatch):
    monkeypatch.setattr(mcp_main, "_fetch_json", lambda _url, *, timeout_seconds: ({"results": []}, 200))

    payload, status_code = mcp_main._web_search({"query": "hello", "top_k": 2})

    assert status_code == 200
    assert payload == {"query": "hello", "results": []}


def test_web_search_caps_top_k(monkeypatch):
    def fake_fetch_json(_url: str, *, timeout_seconds: float):
        return {
            "results": [
                {"title": f"Result {index}", "url": f"https://example.com/{index}", "content": "", "engine": "test"}
                for index in range(20)
            ]
        }, 200

    monkeypatch.setattr(mcp_main, "_fetch_json", fake_fetch_json)

    payload, status_code = mcp_main._web_search({"query": "hello", "top_k": 999})

    assert status_code == 200
    assert len(payload["results"]) == 10
    assert payload["results"][-1]["rank"] == 10


def test_web_search_rejects_invalid_arguments():
    payload, status_code = mcp_main._web_search({"query": "", "top_k": 2})

    assert status_code == 400
    assert payload["error"] == "invalid_arguments"

    payload, status_code = mcp_main._web_search({"query": "hello", "top_k": "many"})

    assert status_code == 400
    assert payload["message"] == "top_k must be an integer"

    payload, status_code = mcp_main._web_search({"query": "hello", "time_range": "week"})

    assert status_code == 400
    assert payload["message"] == "time_range must be one of day, month, or year"


def test_web_search_maps_backend_timeout(monkeypatch):
    monkeypatch.setattr(mcp_main, "_fetch_json", lambda _url, *, timeout_seconds: (None, 504))

    payload, status_code = mcp_main._web_search({"query": "hello"})

    assert status_code == 504
    assert payload["error"] == "search_timeout"


def test_web_search_maps_backend_unavailable(monkeypatch):
    monkeypatch.setattr(mcp_main, "_fetch_json", lambda _url, *, timeout_seconds: (None, 502))

    payload, status_code = mcp_main._web_search({"query": "hello"})

    assert status_code == 502
    assert payload["error"] == "search_backend_unavailable"
