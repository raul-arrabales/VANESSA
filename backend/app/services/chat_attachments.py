from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, UnidentifiedImageError
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from ..config import AuthConfig
from ..repositories import chat_attachments as attachments_repository
from .attachment_policy import (
    ATTACHMENT_REF_PREFIX,
    AttachmentPolicyError,
    attachment_sha256,
    image_attachment_reference,
    validate_image_attachment_metadata,
)

MAX_IMAGES_PER_MESSAGE = 5

_MIME_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class ChatAttachmentError(ValueError):
    def __init__(self, code: str, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class ResolvedChatAttachment:
    path: Path
    mime_type: str
    download_name: str


def attachment_id_from_ref(value: Any) -> str | None:
    normalized = str(value or "").strip()
    if not normalized.startswith(ATTACHMENT_REF_PREFIX):
        return None
    attachment_id = normalized.removeprefix(ATTACHMENT_REF_PREFIX).strip()
    return attachment_id or None


def image_attachment_ids_from_parts(parts: list[dict[str, Any]]) -> list[str]:
    attachment_ids: list[str] = []
    for part in parts:
        if str(part.get("type") or "") != "image":
            continue
        attachment_id = str(part.get("attachment_id") or "").strip() or attachment_id_from_ref(part.get("image_ref")) or ""
        if attachment_id and attachment_id not in attachment_ids:
            attachment_ids.append(attachment_id)
    return attachment_ids


def save_chat_image_attachment(
    database_url: str,
    *,
    config: AuthConfig,
    owner_user_id: int,
    file: FileStorage | None,
) -> dict[str, Any]:
    if file is None or not file.filename:
        raise ChatAttachmentError("image_file_required", "Image file is required")

    declared_mime = str(file.mimetype or "").strip().lower()
    data = file.read()
    try:
        metadata = validate_image_attachment_metadata(mime_type=declared_mime, byte_size=len(data))
        width, height = _validate_image_bytes(data)
    except AttachmentPolicyError as exc:
        raise ChatAttachmentError(exc.code, exc.message) from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ChatAttachmentError("invalid_image_file", "Image file could not be decoded") from exc

    attachment_id = str(uuid4())
    digest = attachment_sha256(data)
    extension = _MIME_EXTENSIONS.get(metadata["mime_type"], ".img")
    storage_root = _attachment_root(config)
    storage_dir = storage_root / str(owner_user_id) / attachment_id[:2]
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_path = storage_dir / f"{attachment_id}{extension}"
    storage_path.write_bytes(data)

    original_filename = secure_filename(file.filename or "") or None
    try:
        row = attachments_repository.create_attachment(
            database_url,
            attachment_id=attachment_id,
            owner_user_id=owner_user_id,
            mime_type=metadata["mime_type"],
            byte_size=metadata["byte_size"],
            sha256=digest,
            width=width,
            height=height,
            storage_path=str(storage_path),
            original_filename=original_filename,
        )
    except Exception:
        storage_path.unlink(missing_ok=True)
        raise
    return image_attachment_payload(row)


def image_attachment_payload(row: dict[str, Any]) -> dict[str, Any]:
    try:
        reference = image_attachment_reference(
            attachment_id=row.get("id"),
            mime_type=row.get("mime_type"),
            byte_size=row.get("byte_size"),
            width=row.get("width"),
            height=row.get("height"),
            digest_sha256=row.get("sha256"),
        )
    except AttachmentPolicyError as exc:
        raise ChatAttachmentError(exc.code, exc.message) from exc
    return reference


def resolve_chat_attachment_file(
    database_url: str,
    *,
    config: AuthConfig,
    owner_user_id: int,
    attachment_id: str,
) -> ResolvedChatAttachment:
    row = attachments_repository.get_attachment(
        database_url,
        owner_user_id=owner_user_id,
        attachment_id=attachment_id,
    )
    if row is None:
        raise ChatAttachmentError("attachment_not_found", "Attachment not found", status_code=404)

    storage_root = _attachment_root(config).resolve()
    storage_path = Path(str(row.get("storage_path") or "")).resolve()
    try:
        storage_path.relative_to(storage_root)
    except ValueError as exc:
        raise ChatAttachmentError("attachment_storage_invalid", "Attachment storage path is invalid", status_code=500) from exc
    if not storage_path.is_file():
        raise ChatAttachmentError("attachment_file_missing", "Attachment file is missing", status_code=404)
    download_name = str(row.get("original_filename") or "").strip() or f"{attachment_id}{_MIME_EXTENSIONS.get(str(row.get('mime_type') or ''), '')}"
    return ResolvedChatAttachment(
        path=storage_path,
        mime_type=str(row.get("mime_type") or "application/octet-stream"),
        download_name=download_name,
    )


def validate_owned_image_references(
    database_url: str,
    *,
    owner_user_id: int,
    parts: list[dict[str, Any]],
) -> None:
    attachment_ids = image_attachment_ids_from_parts(parts)
    if len(attachment_ids) > MAX_IMAGES_PER_MESSAGE:
        raise ChatAttachmentError(
            "too_many_images",
            f"Messages can include at most {MAX_IMAGES_PER_MESSAGE} images",
        )
    for attachment_id in attachment_ids:
        try:
            UUID(attachment_id)
        except ValueError as exc:
            raise ChatAttachmentError("invalid_attachment_ref", "Image attachment reference is invalid") from exc
    rows = attachments_repository.list_attachments_by_ids(
        database_url,
        owner_user_id=owner_user_id,
        attachment_ids=attachment_ids,
    )
    found_ids = {str(row.get("id") or "") for row in rows}
    missing_ids = [attachment_id for attachment_id in attachment_ids if attachment_id not in found_ids]
    if missing_ids:
        raise ChatAttachmentError("attachment_not_found", "One or more image attachments are unavailable", status_code=404)


def bind_message_attachments(
    database_url: str,
    *,
    owner_user_id: int,
    parts: list[dict[str, Any]],
    conversation_id: str,
    message_id: str,
) -> None:
    attachments_repository.bind_attachments_to_message(
        database_url,
        owner_user_id=owner_user_id,
        attachment_ids=image_attachment_ids_from_parts(parts),
        conversation_id=conversation_id,
        message_id=message_id,
    )


def _attachment_root(config: AuthConfig) -> Path:
    return Path(config.chat_attachments_root).expanduser()


def _validate_image_bytes(data: bytes) -> tuple[int, int]:
    with Image.open(BytesIO(data)) as image:
        image.verify()
    with Image.open(BytesIO(data)) as image:
        width, height = image.size
    if width <= 0 or height <= 0:
        raise ValueError("invalid_image_dimensions")
    return int(width), int(height)
