from __future__ import annotations

from typing import Any

RETRIEVAL_SEARCH_METHODS = ("semantic", "keyword", "hybrid")
RETRIEVAL_QUERY_PREPROCESSING_MODES = ("none", "normalize")
DEFAULT_RETRIEVAL_OPTIONS: dict[str, Any] = {
    "top_k": 5,
    "search_method": "semantic",
    "query_preprocessing": "none",
}


def build_knowledge_base_retrieval_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "query_text": {"type": "string"},
            "top_k": {"type": "integer", "minimum": 1},
            "search_method": {"type": "string", "enum": list(RETRIEVAL_SEARCH_METHODS)},
            "query_preprocessing": {"type": "string", "enum": list(RETRIEVAL_QUERY_PREPROCESSING_MODES)},
            "hybrid_alpha": {"type": "number", "minimum": 0, "maximum": 1},
            "filters": {"type": "object", "additionalProperties": True},
        },
        "required": ["query_text"],
        "additionalProperties": False,
    }


def build_knowledge_base_retrieval_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "knowledge_base_id": {"type": "string"},
            "retrieval": {
                "type": "object",
                "properties": {
                    "index": {"type": "string"},
                    "result_count": {"type": "integer"},
                    "top_k": {"type": "integer"},
                    "search_method": {"type": "string"},
                    "query_preprocessing": {"type": "string"},
                    "hybrid_alpha": {"type": "number"},
                },
                "required": ["index", "result_count", "top_k", "search_method"],
                "additionalProperties": True,
            },
            "results": {"type": "array", "items": {"type": "object"}, "additionalProperties": True},
        },
        "required": ["knowledge_base_id", "retrieval", "results"],
        "additionalProperties": True,
    }
