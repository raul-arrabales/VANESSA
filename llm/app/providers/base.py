from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from app.schemas import ResponseRequest

if TYPE_CHECKING:
    from app.registry import ProviderResult


class ProviderError(Exception):
    def __init__(self, *, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


class RoutedModelProvider(Protocol):
    def generate(self, request: ResponseRequest, *, upstream_model: str) -> "ProviderResult":
        """Generates a response from the incoming request."""
