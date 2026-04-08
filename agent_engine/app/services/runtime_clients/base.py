from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class RuntimeClientError(RuntimeError):
    def __init__(self, *, code: str, message: str, status_code: int, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class LlmRuntimeClientError(RuntimeClientError):
    pass


class VectorStoreRuntimeClientError(RuntimeClientError):
    pass


class EmbeddingsRuntimeClientError(RuntimeClientError):
    pass


class ToolRuntimeClientError(RuntimeClientError):
    pass


class LlmRuntimeClient(ABC):
    def __init__(self, *, deployment_profile: dict[str, Any], llm_binding: dict[str, Any]):
        self.deployment_profile = deployment_profile
        self.llm_binding = llm_binding

    @abstractmethod
    def chat_completion(
        self,
        *,
        requested_model: str | None,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


class VectorStoreRuntimeClient(ABC):
    def __init__(self, *, deployment_profile: dict[str, Any], vector_binding: dict[str, Any]):
        self.deployment_profile = deployment_profile
        self.vector_binding = vector_binding

    @abstractmethod
    def query(
        self,
        *,
        index_name: str,
        search_method: str,
        embedding: list[float] | None,
        top_k: int,
        filters: dict[str, Any],
        query_text: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


class EmbeddingsRuntimeClient(ABC):
    def __init__(self, *, deployment_profile: dict[str, Any], embeddings_binding: dict[str, Any]):
        self.deployment_profile = deployment_profile
        self.embeddings_binding = embeddings_binding

    @abstractmethod
    def embed_texts(
        self,
        *,
        texts: list[str],
    ) -> dict[str, Any]:
        raise NotImplementedError


class McpToolRuntimeClient(ABC):
    def __init__(self, *, deployment_profile: dict[str, Any], mcp_binding: dict[str, Any]):
        self.deployment_profile = deployment_profile
        self.mcp_binding = mcp_binding

    @abstractmethod
    def invoke(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        request_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError


class SandboxToolRuntimeClient(ABC):
    def __init__(self, *, deployment_profile: dict[str, Any], sandbox_binding: dict[str, Any]):
        self.deployment_profile = deployment_profile
        self.sandbox_binding = sandbox_binding

    @abstractmethod
    def execute_python(
        self,
        *,
        code: str,
        input_payload: Any,
        timeout_seconds: int,
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError
