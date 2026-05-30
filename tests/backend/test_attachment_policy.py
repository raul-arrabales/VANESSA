import pytest

from backend.app.services.attachment_policy import (
    AttachmentPolicyError,
    AttachmentValidationPolicy,
    attachment_sha256,
    image_attachment_reference,
    safe_attachment_log_metadata,
    validate_image_attachment_metadata,
)


def test_validate_image_attachment_metadata_normalizes_safe_values() -> None:
    assert validate_image_attachment_metadata(mime_type=" IMAGE/PNG ", byte_size="42") == {
        "mime_type": "image/png",
        "byte_size": 42,
    }


def test_validate_image_attachment_metadata_rejects_unsupported_mime_type() -> None:
    with pytest.raises(AttachmentPolicyError) as exc_info:
        validate_image_attachment_metadata(mime_type="application/pdf", byte_size=42)

    assert exc_info.value.code == "unsupported_image_mime_type"


def test_validate_image_attachment_metadata_rejects_oversized_images() -> None:
    policy = AttachmentValidationPolicy(max_image_bytes=10)

    with pytest.raises(AttachmentPolicyError) as exc_info:
        validate_image_attachment_metadata(mime_type="image/jpeg", byte_size=11, policy=policy)

    assert exc_info.value.code == "image_too_large"


def test_safe_attachment_log_metadata_strips_payload_like_fields() -> None:
    assert safe_attachment_log_metadata({
        "mime_type": "image/png",
        "byte_size": 42,
        "data_base64": "secret",
        "bytes": b"secret",
        "payload": "secret",
    }) == {
        "mime_type": "image/png",
        "byte_size": 42,
    }


def test_attachment_sha256_returns_content_digest() -> None:
    assert attachment_sha256(b"vanessa") == "a051e62c16c385ab646c4161a67a338bc8e7efdff2c797e53fcdb72b9fc2b4d0"


def test_image_attachment_reference_returns_upload_reference_shape() -> None:
    assert image_attachment_reference(
        attachment_id="image-1",
        mime_type="image/webp",
        byte_size=128,
        alt_text="Plate photo",
        width="640",
        height=480,
        digest_sha256="digest",
    ) == {
        "attachment_id": "image-1",
        "image_ref": "attachment://image-1",
        "mime_type": "image/webp",
        "byte_size": 128,
        "alt_text": "Plate photo",
        "sha256": "digest",
        "width": 640,
        "height": 480,
    }
