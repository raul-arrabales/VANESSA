from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

ALLOWED_IMAGE_MIME_TYPES = frozenset({"image/png", "image/jpeg", "image/webp", "image/gif"})
DEFAULT_MAX_IMAGE_BYTES = 10 * 1024 * 1024
ATTACHMENT_REF_PREFIX = "attachment://"


class AttachmentPolicyError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class AttachmentValidationPolicy:
    allowed_image_mime_types: frozenset[str] = ALLOWED_IMAGE_MIME_TYPES
    max_image_bytes: int = DEFAULT_MAX_IMAGE_BYTES


def normalize_mime_type(value: Any) -> str:
    return str(value or "").strip().lower()


def validate_image_attachment_metadata(
    *,
    mime_type: Any,
    byte_size: Any,
    policy: AttachmentValidationPolicy | None = None,
) -> dict[str, Any]:
    active_policy = policy or AttachmentValidationPolicy()
    normalized_mime = normalize_mime_type(mime_type)
    if normalized_mime not in active_policy.allowed_image_mime_types:
        raise AttachmentPolicyError("unsupported_image_mime_type", "Image MIME type is not supported")
    try:
        normalized_size = int(byte_size)
    except (TypeError, ValueError) as exc:
        raise AttachmentPolicyError("invalid_image_size", "Image byte size is required") from exc
    if normalized_size <= 0:
        raise AttachmentPolicyError("invalid_image_size", "Image byte size must be greater than zero")
    if normalized_size > active_policy.max_image_bytes:
        raise AttachmentPolicyError("image_too_large", "Image exceeds the maximum allowed size")
    return {"mime_type": normalized_mime, "byte_size": normalized_size}


def attachment_sha256(data: bytes) -> str:
    return sha256(data).hexdigest()


def image_attachment_reference(
    *,
    attachment_id: Any,
    mime_type: Any,
    byte_size: Any,
    alt_text: Any = None,
    width: Any = None,
    height: Any = None,
    digest_sha256: Any = None,
    policy: AttachmentValidationPolicy | None = None,
) -> dict[str, Any]:
    normalized_id = str(attachment_id or "").strip()
    if not normalized_id:
        raise AttachmentPolicyError("invalid_attachment_id", "Attachment id is required")
    metadata = validate_image_attachment_metadata(mime_type=mime_type, byte_size=byte_size, policy=policy)
    reference: dict[str, Any] = {
        "attachment_id": normalized_id,
        "image_ref": f"{ATTACHMENT_REF_PREFIX}{normalized_id}",
        **metadata,
    }
    normalized_alt = str(alt_text or "").strip()
    normalized_digest = str(digest_sha256 or "").strip()
    if normalized_alt:
        reference["alt_text"] = normalized_alt
    if normalized_digest:
        reference["sha256"] = normalized_digest
    for key, value in {"width": width, "height": height}.items():
        if value is None:
            continue
        try:
            normalized_dimension = int(value)
        except (TypeError, ValueError) as exc:
            raise AttachmentPolicyError(f"invalid_image_{key}", f"Image {key} must be a number") from exc
        if normalized_dimension > 0:
            reference[key] = normalized_dimension
    return reference


def safe_attachment_log_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Return metadata that is safe for logs/telemetry; never include payload bytes."""
    return {
        key: value
        for key, value in metadata.items()
        if key not in {"data_base64", "bytes", "content", "raw", "payload"}
    }
