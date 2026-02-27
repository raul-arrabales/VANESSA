from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from app.app import app  # noqa: E402


def test_expected_routes_are_registered() -> None:
    rules = {rule.rule for rule in app.url_map.iter_rules()}

    expected = {
        "/auth/register",
        "/auth/login",
        "/auth/logout",
        "/auth/me",
        "/models/catalog",
        "/models/discovery/huggingface",
        "/v1/models/catalog",
        "/v1/models/discovery/huggingface",
        "/v1/models/downloads",
        "/v1/models/inference",
        "/v1/models/generate",
        "/v1/model-governance/assignments",
        "/v1/model-governance/access-assignments",
        "/v1/model-governance/allowed",
        "/v1/model-governance/enabled",
        "/voice/wake-events",
        "/voice/health",
        "/v1/registry/<entity_type>",
        "/v1/runtime/profile",
        "/v1/policy/rules",
        "/v1/agent-executions",
        "/v1/agent-executions/<execution_id>",
    }

    missing = expected - rules
    assert not missing, f"Missing expected routes: {sorted(missing)}"


def test_no_duplicate_path_method_bindings() -> None:
    seen: set[tuple[str, str]] = set()
    for rule in app.url_map.iter_rules():
        methods = set(rule.methods or set()) - {"HEAD", "OPTIONS"}
        for method in methods:
            key = (rule.rule, method)
            assert key not in seen, f"Duplicate route binding for {key}"
            seen.add(key)
