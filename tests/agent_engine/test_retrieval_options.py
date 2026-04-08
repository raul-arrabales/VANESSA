from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "tests"))

from agent_engine.app.retrieval import options as retrieval_options  # noqa: E402
from retrieval_option_normalization_fixtures import (  # noqa: E402
    INVALID_RETRIEVAL_OPTION_CASES,
    VALID_RETRIEVAL_OPTION_CASES,
)


@pytest.mark.parametrize("case", VALID_RETRIEVAL_OPTION_CASES, ids=[case["name"] for case in VALID_RETRIEVAL_OPTION_CASES])
def test_normalize_retrieval_request_matches_canonical_cases(case: dict[str, object]):
    request = retrieval_options.normalize_retrieval_request(case["agent_execution_input"])

    assert request is not None
    assert request.index == "kb_product_docs"
    assert request.query == case["expected"]["query_text"]
    assert request.top_k == case["expected"]["top_k"]
    assert request.search_method == case["expected"]["search_method"]
    assert request.query_preprocessing == case["expected"]["query_preprocessing"]
    assert request.hybrid_alpha == case["expected"]["hybrid_alpha"]


@pytest.mark.parametrize("case", INVALID_RETRIEVAL_OPTION_CASES, ids=[case["name"] for case in INVALID_RETRIEVAL_OPTION_CASES])
def test_normalize_retrieval_request_rejects_invalid_parity_cases(case: dict[str, object]):
    with pytest.raises(ValueError) as exc_info:
        retrieval_options.normalize_retrieval_request(case["agent_execution_input"])

    assert str(exc_info.value) == "invalid_retrieval_input"


def test_normalize_retrieval_request_uses_last_user_message_when_prompt_and_query_are_absent():
    request = retrieval_options.normalize_retrieval_request(
        {
            "messages": [
                {"role": "assistant", "content": "Earlier response"},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "First line"},
                        {"type": "text", "text": "Second line"},
                    ],
                },
            ],
            "retrieval": {
                "index": "kb_product_docs",
            },
        }
    )

    assert request is not None
    assert request.query == "First line\nSecond line"
    assert request.top_k == 5
    assert request.search_method == "semantic"
    assert request.query_preprocessing == "none"


def test_normalize_retrieval_request_preserves_explicit_query_and_scalar_filters():
    request = retrieval_options.normalize_retrieval_request(
        {
            "prompt": "Prompt should not win",
            "retrieval": {
                "index": "kb_product_docs",
                "query": "Explicit retrieval query",
                "filters": {
                    "tenant": "ops",
                    "published": True,
                    "priority": 3,
                    "weight": 0.75,
                },
            },
        }
    )

    assert request is not None
    assert request.query == "Explicit retrieval query"
    assert request.filters == {
        "tenant": "ops",
        "published": True,
        "priority": 3,
        "weight": 0.75,
    }


def test_normalize_retrieval_request_rejects_invalid_filters():
    with pytest.raises(ValueError) as exc_info:
        retrieval_options.normalize_retrieval_request(
            {
                "retrieval": {
                    "index": "kb_product_docs",
                    "query": "hello",
                    "filters": {"tags": ["a", "b"]},
                }
            }
        )

    assert str(exc_info.value) == "invalid_retrieval_input"
