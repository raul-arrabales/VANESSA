from __future__ import annotations

from typing import Literal

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
    content: list[MessagePart] = Field(min_length=1)


class ResponseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = Field(min_length=1)
    input: list[Message] = Field(min_length=1)
    temperature: float | None = None
    max_tokens: int | None = None


class NormalizedOutputMessage(BaseModel):
    role: Literal["assistant"]
    content: list[TextPart]


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ErrorEnvelope(BaseModel):
    code: str
    message: str


class ResponseEnvelope(BaseModel):
    model: str
    output: list[NormalizedOutputMessage]
    usage: Usage
    error: ErrorEnvelope | None = None
