from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Protocol

from app.schemas import EmbeddingRequest, ResponseRequest

if TYPE_CHECKING:
    from app.registry import EmbeddingResult, ProviderResult


class ProviderError(Exception):
    def __init__(self, *, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


class RoutedModelProvider(Protocol):
    def generate(self, request: ResponseRequest, *, upstream_model: str) -> "ProviderResult":
        """Generates a response from the incoming request."""

    def generate_stream(
        self,
        request: ResponseRequest,
        *,
        upstream_model: str,
    ) -> Iterator[dict[str, object]]:
        """Streams response deltas from the incoming request."""

    def embed(self, request: EmbeddingRequest, *, upstream_model: str) -> "EmbeddingResult":
        """Generates embeddings from the incoming request."""
