from __future__ import annotations

from typing import Any

from .base import EmbeddingsRuntimeClient, EmbeddingsRuntimeClientError
from .resolution import binding_timeout_seconds, resolve_effective_embedding_model
from .secrets import openai_compatible_headers
from .transport import JsonRequestFn, request_json_or_raise


def embeddings_request_failed_code(status_code: int) -> str:
    if status_code == 504:
        return "embeddings_runtime_timeout"
    if status_code >= 502:
        return "embeddings_runtime_upstream_unavailable"
    return "embeddings_runtime_request_failed"


class OpenAICompatibleEmbeddingsRuntimeClient(EmbeddingsRuntimeClient):
    def __init__(
        self,
        *,
        deployment_profile: dict[str, Any],
        embeddings_binding: dict[str, Any],
        request_json: JsonRequestFn,
    ):
        super().__init__(deployment_profile=deployment_profile, embeddings_binding=embeddings_binding)
        self.request_json = request_json

    def embed_texts(
        self,
        *,
        texts: list[str],
    ) -> dict[str, Any]:
        selected_model_id, runtime_model_id = resolve_effective_embedding_model(
            self.embeddings_binding,
            request_json=self.request_json,
        )
        response_payload, status_code = request_json_or_raise(
            request_json=self.request_json,
            error_cls=EmbeddingsRuntimeClientError,
            binding=self.embeddings_binding,
            url=self._embeddings_url(),
            method="POST",
            payload={
                "model": runtime_model_id,
                "input": texts,
            },
            headers=openai_compatible_headers(self.embeddings_binding, error_cls=EmbeddingsRuntimeClientError),
            timeout_seconds=binding_timeout_seconds(self.embeddings_binding),
            unavailable_code="embeddings_runtime_unreachable",
            unavailable_message="Embeddings runtime unavailable",
            request_failed_code=embeddings_request_failed_code,
            request_failed_message="Embeddings runtime request failed",
        )
        embeddings = extract_embeddings(response_payload)
        if not embeddings:
            raise EmbeddingsRuntimeClientError(
                code="embeddings_runtime_request_failed",
                message="Embeddings runtime returned no vectors",
                status_code=502,
                details={
                    "provider_slug": self.embeddings_binding.get("slug"),
                    "status_code": 502,
                    "upstream": response_payload,
                },
            )
        return {
            "embeddings": embeddings,
            "dimension": len(embeddings[0]) if embeddings else 0,
            "status_code": status_code,
            "requested_model": selected_model_id,
        }

    def _embeddings_url(self) -> str:
        config = self.embeddings_binding.get("config") if isinstance(self.embeddings_binding.get("config"), dict) else {}
        embeddings_path = str(config.get("embeddings_path", "/v1/embeddings")).strip() or "/v1/embeddings"
        endpoint_url = str(self.embeddings_binding.get("endpoint_url", "")).rstrip("/")
        return endpoint_url + embeddings_path


def extract_embeddings(payload: dict[str, Any]) -> list[list[float]]:
    data = payload.get("data")
    if not isinstance(data, list):
        return []
    embeddings: list[list[float]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        raw_embedding = item.get("embedding")
        if not isinstance(raw_embedding, list):
            continue
        vector: list[float] = []
        for value in raw_embedding:
            if isinstance(value, bool):
                vector = []
                break
            try:
                vector.append(float(value))
            except (TypeError, ValueError):
                vector = []
                break
        if vector:
            embeddings.append(vector)
    return embeddings
