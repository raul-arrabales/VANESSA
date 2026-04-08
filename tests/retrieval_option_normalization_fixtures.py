from __future__ import annotations

VALID_RETRIEVAL_OPTION_CASES = [
    {
        "name": "default_semantic_request",
        "backend_payload": {"query_text": "hello"},
        "agent_execution_input": {
            "prompt": "hello",
            "retrieval": {
                "index": "kb_product_docs",
            },
        },
        "expected": {
            "query_text": "hello",
            "top_k": 5,
            "search_method": "semantic",
            "query_preprocessing": "none",
            "hybrid_alpha": None,
        },
    },
    {
        "name": "keyword_request_with_preprocessing",
        "backend_payload": {
            "query_text": "Raul!!!",
            "top_k": 7,
            "search_method": "keyword",
            "query_preprocessing": "normalize",
        },
        "agent_execution_input": {
            "retrieval": {
                "index": "kb_product_docs",
                "query": "Raul!!!",
                "top_k": 7,
                "search_method": "keyword",
                "query_preprocessing": "normalize",
            },
        },
        "expected": {
            "query_text": "Raul!!!",
            "top_k": 7,
            "search_method": "keyword",
            "query_preprocessing": "normalize",
            "hybrid_alpha": None,
        },
    },
    {
        "name": "hybrid_request_with_alpha",
        "backend_payload": {
            "query_text": "How does hybrid search work?",
            "top_k": 3,
            "search_method": "hybrid",
            "query_preprocessing": "normalize",
            "hybrid_alpha": 0.65,
        },
        "agent_execution_input": {
            "retrieval": {
                "index": "kb_product_docs",
                "query": "How does hybrid search work?",
                "top_k": 3,
                "search_method": "hybrid",
                "query_preprocessing": "normalize",
                "hybrid_alpha": 0.65,
            },
        },
        "expected": {
            "query_text": "How does hybrid search work?",
            "top_k": 3,
            "search_method": "hybrid",
            "query_preprocessing": "normalize",
            "hybrid_alpha": 0.65,
        },
    },
]


INVALID_RETRIEVAL_OPTION_CASES = [
    {
        "name": "invalid_top_k",
        "backend_payload": {"query_text": "hello", "top_k": 0},
        "agent_execution_input": {
            "retrieval": {
                "index": "kb_product_docs",
                "query": "hello",
                "top_k": 0,
            },
        },
        "backend_error_code": "invalid_top_k",
    },
    {
        "name": "invalid_search_method",
        "backend_payload": {"query_text": "hello", "search_method": "lexical"},
        "agent_execution_input": {
            "retrieval": {
                "index": "kb_product_docs",
                "query": "hello",
                "search_method": "lexical",
            },
        },
        "backend_error_code": "invalid_search_method",
    },
    {
        "name": "invalid_query_preprocessing",
        "backend_payload": {
            "query_text": "hello",
            "query_preprocessing": "strip_all",
        },
        "agent_execution_input": {
            "retrieval": {
                "index": "kb_product_docs",
                "query": "hello",
                "query_preprocessing": "strip_all",
            },
        },
        "backend_error_code": "invalid_query_preprocessing",
    },
    {
        "name": "invalid_hybrid_alpha",
        "backend_payload": {
            "query_text": "hello",
            "search_method": "hybrid",
            "hybrid_alpha": 2.0,
        },
        "agent_execution_input": {
            "retrieval": {
                "index": "kb_product_docs",
                "query": "hello",
                "search_method": "hybrid",
                "hybrid_alpha": 2.0,
            },
        },
        "backend_error_code": "invalid_hybrid_alpha",
    },
]
