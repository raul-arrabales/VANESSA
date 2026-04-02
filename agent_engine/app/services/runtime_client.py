from __future__ import annotations

from typing import Any

from .runtime_clients.base import (
    EmbeddingsRuntimeClient,
    EmbeddingsRuntimeClientError,
    LlmRuntimeClient,
    LlmRuntimeClientError,
    McpToolRuntimeClient,
    SandboxToolRuntimeClient,
    ToolRuntimeClientError,
    VectorStoreRuntimeClient,
    VectorStoreRuntimeClientError,
)
from .runtime_clients.embeddings import OpenAICompatibleEmbeddingsRuntimeClient
from .runtime_clients.llm import OpenAICompatibleLlmRuntimeClient
from .runtime_clients.resolution import (
    coerce_platform_runtime,
    require_binding,
    require_supported_adapter_kind,
)
from .runtime_clients.tool_runtime import HttpMcpToolRuntimeClient, HttpSandboxToolRuntimeClient
from .runtime_clients.transport import (
    DEFAULT_HTTP_TIMEOUT_SECONDS as _DEFAULT_HTTP_TIMEOUT_SECONDS,
    http_json_request as _http_json_request,
)
from .runtime_clients.vector_store import QdrantVectorStoreRuntimeClient, WeaviateVectorStoreRuntimeClient

_DEFAULT_HTTP_TIMEOUT_SECONDS = _DEFAULT_HTTP_TIMEOUT_SECONDS
http_json_request = _http_json_request


def build_llm_runtime_client(platform_runtime: dict[str, Any]) -> LlmRuntimeClient:
    deployment_profile, capabilities = coerce_platform_runtime(
        platform_runtime,
        error_cls=LlmRuntimeClientError,
    )
    llm_binding = require_binding(
        capabilities,
        capability_key="llm_inference",
        missing_code="missing_llm_runtime",
        missing_message="platform_runtime is missing llm_inference binding",
        error_cls=LlmRuntimeClientError,
    )
    require_supported_adapter_kind(
        llm_binding,
        supported={"openai_compatible_llm"},
        unsupported_message="Unsupported LLM runtime adapter",
        error_cls=LlmRuntimeClientError,
    )
    return OpenAICompatibleLlmRuntimeClient(
        deployment_profile=deployment_profile,
        llm_binding=llm_binding,
        request_json=http_json_request,
    )


def build_embeddings_runtime_client(platform_runtime: dict[str, Any]) -> EmbeddingsRuntimeClient:
    deployment_profile, capabilities = coerce_platform_runtime(
        platform_runtime,
        error_cls=EmbeddingsRuntimeClientError,
    )
    embeddings_binding = require_binding(
        capabilities,
        capability_key="embeddings",
        missing_code="missing_embeddings_runtime",
        missing_message="platform_runtime is missing embeddings binding",
        error_cls=EmbeddingsRuntimeClientError,
    )
    require_supported_adapter_kind(
        embeddings_binding,
        supported={"openai_compatible_embeddings"},
        unsupported_message="Unsupported embeddings runtime adapter",
        error_cls=EmbeddingsRuntimeClientError,
    )
    return OpenAICompatibleEmbeddingsRuntimeClient(
        deployment_profile=deployment_profile,
        embeddings_binding=embeddings_binding,
        request_json=http_json_request,
    )


def build_vector_store_runtime_client(platform_runtime: dict[str, Any]) -> VectorStoreRuntimeClient:
    deployment_profile, capabilities = coerce_platform_runtime(
        platform_runtime,
        error_cls=VectorStoreRuntimeClientError,
    )
    vector_binding = require_binding(
        capabilities,
        capability_key="vector_store",
        missing_code="missing_vector_runtime",
        missing_message="platform_runtime is missing vector_store binding",
        error_cls=VectorStoreRuntimeClientError,
    )
    adapter_kind = require_supported_adapter_kind(
        vector_binding,
        supported={"weaviate_http", "qdrant_http"},
        unsupported_message="Unsupported vector runtime adapter",
        error_cls=VectorStoreRuntimeClientError,
    )
    if adapter_kind == "weaviate_http":
        return WeaviateVectorStoreRuntimeClient(
            deployment_profile=deployment_profile,
            vector_binding=vector_binding,
            request_json=http_json_request,
        )
    return QdrantVectorStoreRuntimeClient(
        deployment_profile=deployment_profile,
        vector_binding=vector_binding,
        request_json=http_json_request,
    )


def build_mcp_tool_runtime_client(platform_runtime: dict[str, Any]) -> McpToolRuntimeClient:
    deployment_profile, capabilities = coerce_platform_runtime(
        platform_runtime,
        error_cls=ToolRuntimeClientError,
    )
    mcp_binding = require_binding(
        capabilities,
        capability_key="mcp_runtime",
        missing_code="missing_tool_runtime",
        missing_message="platform_runtime is missing mcp_runtime binding",
        error_cls=ToolRuntimeClientError,
    )
    require_supported_adapter_kind(
        mcp_binding,
        supported={"mcp_http"},
        unsupported_message="Unsupported MCP runtime adapter",
        error_cls=ToolRuntimeClientError,
    )
    return HttpMcpToolRuntimeClient(
        deployment_profile=deployment_profile,
        mcp_binding=mcp_binding,
        request_json=http_json_request,
    )


def build_sandbox_tool_runtime_client(platform_runtime: dict[str, Any]) -> SandboxToolRuntimeClient:
    deployment_profile, capabilities = coerce_platform_runtime(
        platform_runtime,
        error_cls=ToolRuntimeClientError,
    )
    sandbox_binding = require_binding(
        capabilities,
        capability_key="sandbox_execution",
        missing_code="missing_tool_runtime",
        missing_message="platform_runtime is missing sandbox_execution binding",
        error_cls=ToolRuntimeClientError,
    )
    require_supported_adapter_kind(
        sandbox_binding,
        supported={"sandbox_http"},
        unsupported_message="Unsupported sandbox runtime adapter",
        error_cls=ToolRuntimeClientError,
    )
    return HttpSandboxToolRuntimeClient(
        deployment_profile=deployment_profile,
        sandbox_binding=sandbox_binding,
        request_json=http_json_request,
    )


__all__ = [
    "EmbeddingsRuntimeClient",
    "EmbeddingsRuntimeClientError",
    "LlmRuntimeClient",
    "LlmRuntimeClientError",
    "McpToolRuntimeClient",
    "SandboxToolRuntimeClient",
    "ToolRuntimeClientError",
    "VectorStoreRuntimeClient",
    "VectorStoreRuntimeClientError",
    "_DEFAULT_HTTP_TIMEOUT_SECONDS",
    "build_embeddings_runtime_client",
    "build_llm_runtime_client",
    "build_mcp_tool_runtime_client",
    "build_sandbox_tool_runtime_client",
    "build_vector_store_runtime_client",
    "http_json_request",
]
