from fastapi import FastAPI, HTTPException

from app.config import load_llm_config
from app.providers.base import ProviderError
from app.registry import ModelInfo, registry
from app.schemas import (
    ErrorEnvelope,
    ImageUrlPart,
    NormalizedOutputMessage,
    ResponseEnvelope,
    ResponseRequest,
    TextPart,
    Usage,
)

SERVICE_NAME = "llm"
SERVICE_VERSION = "0.1.0"

app = FastAPI(title="VANESSA LLM Service", version=SERVICE_VERSION)

registry.configure(load_llm_config())


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
    }


@app.get("/v1/models")
def list_models() -> dict[str, object]:
    models: list[ModelInfo] = registry.list_models()
    data: list[dict[str, object]] = []
    for model in models:
        data.append(
            {
                "id": model.id,
                "object": "model",
                "owned_by": model.provider_type,
                "display_name": model.display_name,
                "capabilities": {
                    "text": model.capabilities.text,
                    "image_input": model.capabilities.image_input,
                },
                "status": model.status,
                "provider_type": model.provider_type,
                "provider_config_ref": model.provider_config_ref,
                "metadata": model.metadata,
            }
        )
    return {"object": "list", "data": data}


def _contains_image_parts(request: ResponseRequest) -> bool:
    return any(
        isinstance(part, ImageUrlPart)
        for message in request.input
        for part in message.content
    )


def _build_response(request: ResponseRequest) -> ResponseEnvelope:
    try:
        resolved_model = registry.resolve_model(request.model)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=ErrorEnvelope(code="model_not_found", message=str(exc)).model_dump(),
        ) from exc

    if _contains_image_parts(request) and not resolved_model.model.capabilities.image_input:
        raise HTTPException(
            status_code=422,
            detail=ErrorEnvelope(
                code="unsupported_input",
                message=f"Model '{request.model}' does not support image input.",
            ).model_dump(),
        )

    result = None
    last_provider_error: ProviderError | None = None
    candidates = [resolved_model, *registry.failover_models(request.model)]
    for candidate in candidates:
        try:
            result = candidate.provider.generate(
                request, upstream_model=candidate.model.upstream_model or candidate.model.id
            )
            last_provider_error = None
            break
        except ProviderError as exc:
            last_provider_error = exc

    if result is None:
        assert last_provider_error is not None
        raise HTTPException(
            status_code=last_provider_error.status_code,
            detail=ErrorEnvelope(
                code=last_provider_error.code,
                message=last_provider_error.message,
            ).model_dump(),
        )

    usage = Usage(
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        total_tokens=result.prompt_tokens + result.completion_tokens,
    )
    return ResponseEnvelope(
        model=request.model,
        output=[
            NormalizedOutputMessage(
                role="assistant",
                content=[TextPart(type="text", text=result.output_text)],
            )
        ],
        usage=usage,
    )


@app.post("/v1/responses", response_model=ResponseEnvelope)
def create_response(request: ResponseRequest) -> ResponseEnvelope:
    return _build_response(request)


@app.post("/v1/chat/completions", response_model=ResponseEnvelope)
def create_chat_completion(request: ResponseRequest) -> ResponseEnvelope:
    return _build_response(request)
