from backend.app.services.message_content import (
    MESSAGE_CONTENT_CONTRACT,
    content_text,
    coerce_llm_messages,
    image_ref_part,
    message_content_parts,
    normalize_content_parts,
    text_part,
)


def test_message_content_uses_text_fallback_as_persisted_summary() -> None:
    assert message_content_parts({"content": "hello"}) == [text_part("hello")]
    assert content_text({"content": "hello"}) == "hello"


def test_message_content_prefers_rich_parts_from_metadata_json() -> None:
    message = {
        "content": "fallback",
        "metadata_json": {
            "content_parts": [
                {"type": "text", "text": "first"},
                {"type": "text", "text": "second"},
            ],
        },
    }

    assert message_content_parts(message) == [text_part("first"), text_part("second")]
    assert content_text(message) == "first\nsecond"


def test_image_parts_are_reference_shaped_but_disabled_by_default() -> None:
    image_part = image_ref_part(image_ref="attachment://image-1", mime_type="image/png", alt_text="diagram")

    assert normalize_content_parts([image_part]) == []
    assert normalize_content_parts([image_part], allow_image_parts=True) == [image_part]


def test_coerce_llm_messages_keeps_allowed_roles_and_text_parts() -> None:
    messages = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content_parts": [{"type": "text", "text": "hi"}]},
        {"role": "system", "content": "ignore"},
        {"role": "user", "content": ""},
    ]

    assert coerce_llm_messages(messages, allowed_roles={"user", "assistant"}) == [
        {"role": "user", "content": [text_part("hello")]},
        {"role": "assistant", "content": [text_part("hi")]},
    ]


def test_message_content_contract_names_persistence_boundary() -> None:
    assert "metadata_json.content_parts" in MESSAGE_CONTENT_CONTRACT
    assert "text-only summary" in MESSAGE_CONTENT_CONTRACT
