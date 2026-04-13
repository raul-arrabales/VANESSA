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
        "/v1/content/quote-of-the-day",
        "/v1/quotes/summary",
        "/v1/quotes",
        "/v1/quotes/<int:quote_id>",
        "/v1/modelops/models",
        "/v1/modelops/models/<model_id>",
        "/v1/modelops/models/<model_id>/usage",
        "/v1/modelops/models/<model_id>/validations",
        "/v1/modelops/models/<model_id>/tests",
        "/v1/modelops/models/<model_id>/test-runtimes",
        "/v1/modelops/models/<model_id>/test",
        "/v1/modelops/models/<model_id>/register",
        "/v1/modelops/models/<model_id>/validate",
        "/v1/modelops/models/<model_id>/activate",
        "/v1/modelops/models/<model_id>/deactivate",
        "/v1/modelops/models/<model_id>/unregister",
        "/v1/modelops/models/<model_id>/credential",
        "/v1/modelops/credentials",
        "/v1/modelops/credentials/<credential_id>/revoke",
        "/v1/modelops/catalog",
        "/v1/modelops/local-artifacts",
        "/v1/modelops/sharing",
        "/v1/modelops/discovery/huggingface",
        "/v1/modelops/discovery/huggingface/<path:source_id>",
        "/v1/modelops/downloads",
        "/v1/modelops/downloads/<job_id>",
        "/v1/playgrounds/sessions",
        "/v1/playgrounds/sessions/<session_id>",
        "/v1/playgrounds/sessions/<session_id>/messages",
        "/v1/playgrounds/sessions/<session_id>/messages/stream",
        "/v1/playgrounds/options",
        "/v1/agent-projects",
        "/v1/agent-projects/<project_id>",
        "/v1/agent-projects/<project_id>/validate",
        "/v1/agent-projects/<project_id>/publish",
        "/v1/context/schema-profiles",
        "/v1/context/vectorization-options",
        "/v1/context/source-directories",
        "/v1/context/knowledge-bases",
        "/v1/context/knowledge-bases/<knowledge_base_id>",
        "/v1/context/knowledge-bases/<knowledge_base_id>/resync",
        "/v1/context/knowledge-bases/<knowledge_base_id>/query",
        "/v1/context/knowledge-bases/<knowledge_base_id>/sources",
        "/v1/context/knowledge-bases/<knowledge_base_id>/sources/<source_id>",
        "/v1/context/knowledge-bases/<knowledge_base_id>/sources/<source_id>/sync",
        "/v1/context/knowledge-bases/<knowledge_base_id>/sync-runs",
        "/v1/context/knowledge-bases/<knowledge_base_id>/documents",
        "/v1/context/knowledge-bases/<knowledge_base_id>/documents/<document_id>",
        "/v1/context/knowledge-bases/<knowledge_base_id>/uploads",
        "/v1/models/inference",
        "/v1/models/generate",
        "/v1/platform/capabilities",
        "/v1/platform/providers",
        "/v1/platform/provider-families",
        "/v1/platform/providers/<provider_id>/validate",
        "/v1/platform/providers/<provider_id>/loaded-model",
        "/v1/platform/providers/<provider_id>",
        "/v1/platform/deployments",
        "/v1/platform/activation-audit",
        "/v1/platform/deployments/<deployment_profile_id>",
        "/v1/platform/deployments/<deployment_profile_id>/bindings/<capability_key>",
        "/v1/platform/deployments/<deployment_profile_id>/clone",
        "/v1/platform/deployments/<deployment_profile_id>/activate",
        "/v1/platform/embeddings",
        "/v1/platform/vector/indexes/ensure",
        "/v1/platform/vector/documents/upsert",
        "/v1/platform/vector/query",
        "/v1/platform/vector/documents/delete",
        "/v1/catalog/agents",
        "/v1/catalog/agents/<agent_id>",
        "/v1/catalog/agents/<agent_id>/validate",
        "/v1/catalog/tools",
        "/v1/catalog/tools/<tool_id>",
        "/v1/catalog/tools/<tool_id>/validate",
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
