import { describe, expect, it } from "vitest";
import type { PlaygroundMessage } from "../../api/playgrounds";
import { messageContentParts, messageText } from "./messageContent";

function message(overrides: Partial<PlaygroundMessage>): PlaygroundMessage {
  return {
    id: "message-1",
    role: "user",
    content: "",
    metadata: {},
    createdAt: null,
    ...overrides,
  };
}

describe("messageContent", () => {
  it("uses persisted text as the fallback content part", () => {
    const item = message({ content: "hello" });

    expect(messageContentParts(item)).toEqual([{ type: "text", text: "hello" }]);
    expect(messageText(item)).toBe("hello");
  });

  it("prefers rich text parts from metadata", () => {
    const item = message({
      content: "fallback",
      metadata: {
        content_parts: [
          { type: "text", text: "first" },
          { type: "text", text: "second" },
        ],
      },
    });

    expect(messageContentParts(item)).toEqual([
      { type: "text", text: "first" },
      { type: "text", text: "second" },
    ]);
    expect(messageText(item)).toBe("first\nsecond");
  });

  it("normalizes image reference parts without treating them as text", () => {
    const item = message({
      content: "summary",
      content_parts: [
        {
          type: "image",
          image_ref: "attachment://image-1",
          mime_type: "image/png",
          alt_text: "diagram",
          byte_size: 42,
        },
      ],
    });

    expect(messageContentParts(item)).toEqual([
      {
        type: "image",
        image_ref: "attachment://image-1",
        mime_type: "image/png",
        alt_text: "diagram",
        width: undefined,
        height: undefined,
        byte_size: 42,
        sha256: undefined,
      },
    ]);
    expect(messageText(item)).toBe("summary");
  });

  it("preserves unsupported rich parts as explicit placeholders", () => {
    const item = message({
      content_parts: [{ type: "audio", audio_ref: "attachment://audio-1" } as never],
    });

    expect(messageContentParts(item)).toEqual([
      { type: "unsupported", original_type: "audio", reason: "Unsupported message content part" },
    ]);
    expect(messageText(item)).toBe("");
  });
});
