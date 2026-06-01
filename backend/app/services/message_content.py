from __future__ import annotations

from typing import Any

TEXT_PART_TYPE = "text"
IMAGE_PART_TYPE = "image"
MESSAGE_CONTENT_METADATA_KEY = "content_parts"
MESSAGE_CONTENT_CONTRACT = (
    "Persist content TEXT as the text-only summary. Persist rich message parts "
    f"in metadata_json.{MESSAGE_CONTENT_METADATA_KEY}. Image parts use backend-owned "
    "attachment:// references and are retained for UI display, not text-only LLM prompts."
)
SUPPORTED_MESSAGE_PART_TYPES = {TEXT_PART_TYPE, IMAGE_PART_TYPE}


def text_part(text: Any) -> dict[str, str]:
    return {"type": TEXT_PART_TYPE, "text": str(text or "")}


def text_message(role: str, text: Any) -> dict[str, Any]:
    return {"role": role, "content": [text_part(text)]}


def image_ref_part(
    *,
    image_ref: str,
    mime_type: str,
    attachment_id: str | None = None,
    alt_text: str | None = None,
    byte_size: Any = None,
    width: Any = None,
    height: Any = None,
    sha256: Any = None,
) -> dict[str, Any]:
    part: dict[str, Any] = {"type": IMAGE_PART_TYPE, "image_ref": image_ref, "mime_type": mime_type}
    if attachment_id:
        part["attachment_id"] = attachment_id
    if alt_text:
        part["alt_text"] = alt_text
    for key, value in {"byte_size": byte_size, "width": width, "height": height}.items():
        if value is None:
            continue
        try:
            normalized_value = int(value)
        except (TypeError, ValueError):
            continue
        if normalized_value > 0:
            part[key] = normalized_value
    normalized_sha = str(sha256 or "").strip()
    if normalized_sha:
        part["sha256"] = normalized_sha
    return part


def normalize_content_parts(
    value: Any,
    *,
    fallback_text: Any = "",
    allow_image_parts: bool = False,
) -> list[dict[str, Any]]:
    if isinstance(value, list):
        parts: list[dict[str, Any]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            part_type = str(item.get("type") or "").strip().lower()
            if part_type == TEXT_PART_TYPE:
                text = str(item.get("text") or "")
                if text:
                    parts.append(text_part(text))
            if part_type == IMAGE_PART_TYPE and allow_image_parts:
                image_ref = str(item.get("image_ref") or "").strip()
                mime_type = str(item.get("mime_type") or "").strip()
                if image_ref and mime_type:
                    parts.append(image_ref_part(
                        image_ref=image_ref,
                        mime_type=mime_type,
                        attachment_id=str(item.get("attachment_id") or "").strip() or None,
                        alt_text=str(item.get("alt_text") or "").strip() or None,
                        byte_size=item.get("byte_size"),
                        width=item.get("width"),
                        height=item.get("height"),
                        sha256=item.get("sha256"),
                    ))
        if parts:
            return parts
    text = str(fallback_text if fallback_text is not None else value or "")
    return [text_part(text)] if text else []


def content_text(parts_or_message: Any, *, allow_image_parts: bool = False) -> str:
    parts = (
        message_content_parts(parts_or_message, allow_image_parts=allow_image_parts)
        if isinstance(parts_or_message, dict)
        else normalize_content_parts(parts_or_message, allow_image_parts=allow_image_parts)
    )
    return "\n".join(str(part.get("text") or "") for part in parts if str(part.get("type") or "") == TEXT_PART_TYPE).strip()


def message_content_parts(message: dict[str, Any], *, allow_image_parts: bool = False) -> list[dict[str, Any]]:
    metadata = message.get("metadata") if isinstance(message.get("metadata"), dict) else message.get("metadata_json")
    metadata = metadata if isinstance(metadata, dict) else {}
    raw_content = message.get("content")
    raw_parts = message.get("content_parts") if "content_parts" in message else metadata.get(MESSAGE_CONTENT_METADATA_KEY)
    if raw_parts is None and isinstance(raw_content, list):
        raw_parts = raw_content
    return normalize_content_parts(
        raw_parts,
        fallback_text="" if isinstance(raw_content, list) else raw_content,
        allow_image_parts=allow_image_parts,
    )


def coerce_llm_messages(messages: Any, *, allowed_roles: set[str]) -> list[dict[str, Any]]:
    if not isinstance(messages, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip().lower()
        if role not in allowed_roles:
            continue
        parts = message_content_parts(item)
        if not parts:
            continue
        normalized.append({"role": role, "content": parts})
    return normalized
