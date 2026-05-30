import type { PlaygroundMessage, PlaygroundMessageContentPart } from "../../api/playgrounds";

export function textContentPart(text: string): PlaygroundMessageContentPart {
  return { type: "text", text };
}

export function messageContentParts(message: Pick<PlaygroundMessage, "content" | "content_parts" | "metadata">): PlaygroundMessageContentPart[] {
  const rawParts = Array.isArray(message.content_parts)
    ? message.content_parts
    : Array.isArray(message.metadata?.content_parts)
      ? message.metadata.content_parts
      : [];
  const parts = rawParts.filter((part): part is PlaygroundMessageContentPart => Boolean(part && typeof part === "object" && "type" in part));
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
