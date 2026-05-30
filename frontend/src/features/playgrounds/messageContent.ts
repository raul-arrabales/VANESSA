import type { PlaygroundMessage, PlaygroundMessageContentPart } from "../../api/playgrounds";

export function textContentPart(text: string): PlaygroundMessageContentPart {
  return { type: "text", text };
}

export function imageReferenceContentPart(input: Extract<PlaygroundMessageContentPart, { type: "image" }>): PlaygroundMessageContentPart {
  return {
    type: "image",
    image_ref: input.image_ref,
    mime_type: input.mime_type,
    alt_text: input.alt_text,
    width: input.width,
    height: input.height,
    byte_size: input.byte_size,
    sha256: input.sha256,
  };
}

export function messageContentParts(message: Pick<PlaygroundMessage, "content" | "content_parts" | "metadata">): PlaygroundMessageContentPart[] {
  const rawParts = Array.isArray(message.content_parts)
    ? message.content_parts
    : Array.isArray(message.metadata?.content_parts)
      ? message.metadata.content_parts
      : [];
  const parts = rawParts.flatMap((part): PlaygroundMessageContentPart[] => {
    if (!part || typeof part !== "object" || !("type" in part)) {
      return [];
    }
    if (part.type === "text" && typeof part.text === "string") {
      return [textContentPart(part.text)];
    }
    if (part.type === "image" && typeof part.image_ref === "string" && typeof part.mime_type === "string") {
      return [imageReferenceContentPart(part as Extract<PlaygroundMessageContentPart, { type: "image" }>)];
    }
    return [{ type: "unsupported", original_type: String(part.type), reason: "Unsupported message content part" }];
  });
  if (parts.length) {
    return parts;
  }
  return message.content ? [textContentPart(message.content)] : [];
}

export function messageText(message: Pick<PlaygroundMessage, "content" | "content_parts" | "metadata">): string {
  return messageContentParts(message)
    .filter((part): part is Extract<PlaygroundMessageContentPart, { type: "text" }> => part.type === "text")
    .map((part) => part.text)
    .filter(Boolean)
    .join("\n")
    || message.content;
}
