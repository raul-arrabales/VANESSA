from __future__ import annotations

from dataclasses import dataclass

from app.registry import ModelCapabilities, ModelInfo, ProviderResult
from app.schemas import ResponseRequest


@dataclass(frozen=True)
class DummyModelProvider:
    info: ModelInfo = ModelInfo(
        id="dummy",
        display_name="Dummy Test Model",
        capabilities=ModelCapabilities(text=True, image_input=False),
        status="available",
        provider_type="dummy",
    )

    def generate(self, request: ResponseRequest) -> ProviderResult:
        _ = request
        return ProviderResult(
            output_text="Hello, this is the test dummy model.",
            prompt_tokens=8,
            completion_tokens=8,
        )
