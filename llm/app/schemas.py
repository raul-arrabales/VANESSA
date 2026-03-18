from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TextPart(BaseModel):
    type: Literal["text"]
    text: str = Field(min_length=1)


class ImageInputObject(BaseModel):
    url: str | None = None
    b64_json: str | None = None

    @model_validator(mode="after")
    def validate_reference(self) -> "ImageInputObject":
        if not self.url and not self.b64_json:
            raise ValueError("image_url object must include either 'url' or 'b64_json'.")
        return self


class ImageUrlPart(BaseModel):
    type: Literal["image_url"]
    image_url: str | ImageInputObject


MessagePart = TextPart | ImageUrlPart


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: list[MessagePart] = Field(default_factory=list)
    tool_call_id: str | None = None
    tool_calls: list["ToolCall"] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_message(self) -> "Message":
        if self.role == "tool" and not self.tool_call_id:
            raise ValueError("tool role messages must include tool_call_id.")
        if self.tool_call_id is not None and self.role != "tool":
            raise ValueError("tool_call_id is only valid for tool role messages.")
        if not self.content and not self.tool_calls:
            raise ValueError("message must include content or tool_calls.")
        return self


class ToolDefinitionFunction(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    type: Literal["function"] = "function"
    function: ToolDefinitionFunction


class ToolCallFunction(BaseModel):
    name: str = Field(min_length=1)
    arguments: str


class ToolCall(BaseModel):
    id: str = Field(min_length=1)
    type: Literal["function"] = "function"
    function: ToolCallFunction


class ResponseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = Field(min_length=1)
    input: list[Message] = Field(min_length=1)
    temperature: float | None = None
    max_tokens: int | None = None
    tools: list[ToolDefinition] = Field(default_factory=list)


class EmbeddingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = Field(min_length=1)
    input: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_inputs(self) -> "EmbeddingRequest":
        normalized = [item.strip() for item in self.input]
        if any(not item for item in normalized):
            raise ValueError("embedding input items must be non-empty strings.")
        self.input = normalized
        return self


class NormalizedOutputMessage(BaseModel):
    role: Literal["assistant"]
    content: list[TextPart] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_output(self) -> "NormalizedOutputMessage":
        if not self.content and not self.tool_calls:
            raise ValueError("assistant output must include content or tool_calls.")
        return self


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class EmbeddingData(BaseModel):
    object: Literal["embedding"]
    index: int
    embedding: list[float]


class EmbeddingUsage(BaseModel):
    prompt_tokens: int
    total_tokens: int


class ErrorEnvelope(BaseModel):
    code: str
    message: str


class ResponseEnvelope(BaseModel):
    model: str
    output: list[NormalizedOutputMessage]
    usage: Usage
    error: ErrorEnvelope | None = None


class EmbeddingResponseEnvelope(BaseModel):
    object: Literal["list"]
    model: str
    data: list[EmbeddingData]
    usage: EmbeddingUsage
    error: ErrorEnvelope | None = None
