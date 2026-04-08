from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = PROJECT_ROOT / "tests"
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

from app.services import context_management_retrieval_options
from app.services.context_management_retrieval_types import KnowledgeBaseRetrievalOptions
from app.services.platform_types import PlatformControlPlaneError
from retrieval_option_normalization_fixtures import (
    INVALID_RETRIEVAL_OPTION_CASES,
    VALID_RETRIEVAL_OPTION_CASES,
)

@pytest.mark.parametrize("case", VALID_RETRIEVAL_OPTION_CASES, ids=[case["name"] for case in VALID_RETRIEVAL_OPTION_CASES])
def test_normalize_knowledge_base_retrieval_options_matches_canonical_cases(case: dict[str, object]):
    payload = case["backend_payload"]
    expected = case["expected"]

    options = context_management_retrieval_options.normalize_knowledge_base_retrieval_options(payload)

    assert options == KnowledgeBaseRetrievalOptions(
        query_text=expected["query_text"],
        top_k=expected["top_k"],
        search_method=expected["search_method"],
        query_preprocessing=expected["query_preprocessing"],
        hybrid_alpha=expected["hybrid_alpha"],
    )


@pytest.mark.parametrize("case", INVALID_RETRIEVAL_OPTION_CASES, ids=[case["name"] for case in INVALID_RETRIEVAL_OPTION_CASES])
def test_normalize_knowledge_base_retrieval_options_rejects_invalid_parity_cases(case: dict[str, object]):
    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management_retrieval_options.normalize_knowledge_base_retrieval_options(case["backend_payload"])

    assert exc_info.value.code == case["backend_error_code"]


def test_normalize_knowledge_base_retrieval_options_rejects_missing_query_text():
    with pytest.raises(PlatformControlPlaneError) as exc_info:
        context_management_retrieval_options.normalize_knowledge_base_retrieval_options({})

    assert exc_info.value.code == "invalid_query_text"
