import { ApiError, buildUrl, requestJson } from "../auth/authApi";

export type ChatConversationMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  metadata: Record<string, unknown>;
  createdAt: string | null;
};

export type ChatConversationSummary = {
  id: string;
  title: string;
  titleSource: "auto" | "manual";
  modelId: string | null;
  messageCount: number;
  createdAt: string | null;
  updatedAt: string | null;
};

export type ChatConversationDetail = ChatConversationSummary & {
  messages: ChatConversationMessage[];
};

export type SendChatMessageResult = {
  conversation: ChatConversationSummary;
  messages: ChatConversationMessage[];
  output: string;
  response?: Record<string, unknown>;
};

export type StreamChatMessageOptions = {
  onDelta?: (text: string) => void;
  signal?: AbortSignal;
};

export async function listChatConversations(token: string): Promise<ChatConversationSummary[]> {
  const result = await requestJson<{ conversations: ChatConversationSummary[] }>("/v1/chat/conversations", { token });
  return result.conversations;
}

export async function createChatConversation(
  payload: { model_id?: string | null } = {},
  token: string,
): Promise<ChatConversationDetail> {
  const result = await requestJson<{ conversation: ChatConversationDetail }>("/v1/chat/conversations", {
    method: "POST",
    token,
    body: payload,
  });
  return result.conversation;
}

export async function getChatConversation(
  conversationId: string,
  token: string,
): Promise<ChatConversationDetail> {
  const result = await requestJson<{ conversation: ChatConversationDetail }>(
    `/v1/chat/conversations/${encodeURIComponent(conversationId)}`,
    { token },
  );
  return result.conversation;
}

export async function updateChatConversation(
  conversationId: string,
  payload: { title?: string; model_id?: string | null },
  token: string,
): Promise<ChatConversationSummary> {
  const result = await requestJson<{ conversation: ChatConversationSummary }>(
    `/v1/chat/conversations/${encodeURIComponent(conversationId)}`,
    {
      method: "PATCH",
      token,
      body: payload,
    },
  );
  return result.conversation;
}

export async function deleteChatConversation(
  conversationId: string,
  token: string,
): Promise<void> {
  await requestJson<{ deleted: boolean }>(
    `/v1/chat/conversations/${encodeURIComponent(conversationId)}`,
    {
      method: "DELETE",
      token,
    },
  );
}

export async function sendChatMessage(
  conversationId: string,
  payload: { prompt: string },
  token: string,
): Promise<SendChatMessageResult> {
  return requestJson<SendChatMessageResult>(
    `/v1/chat/conversations/${encodeURIComponent(conversationId)}/messages`,
    {
      method: "POST",
      token,
      body: payload,
    },
  );
}

export async function streamChatMessage(
  conversationId: string,
  payload: { prompt: string },
  token: string,
  options: StreamChatMessageOptions = {},
): Promise<SendChatMessageResult> {
  const response = await fetch(
    buildUrl(`/v1/chat/conversations/${encodeURIComponent(conversationId)}/messages/stream`),
    {
      method: "POST",
      headers: {
        Accept: "text/event-stream",
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
      signal: options.signal,
    },
  );

  if (!response.ok) {
    const raw = await response.text();
    const parsed = raw ? JSON.parse(raw) as Record<string, unknown> : {};
    throw new ApiError(
      String(parsed.message ?? parsed.error ?? `HTTP ${response.status}`),
      response.status,
      parsed.error ? String(parsed.error) : undefined,
    );
  }

  if (!response.body) {
    throw new ApiError("Streaming response body missing", 502, "stream_unavailable");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let completed: SendChatMessageResult | null = null;

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });

    let boundaryIndex = buffer.indexOf("\n\n");
    while (boundaryIndex >= 0) {
      const rawEvent = buffer.slice(0, boundaryIndex);
      buffer = buffer.slice(boundaryIndex + 2);
      const parsedEvent = parseSseEvent(rawEvent);
      if (parsedEvent) {
        if (parsedEvent.event === "delta") {
          const text = typeof parsedEvent.data.text === "string" ? parsedEvent.data.text : "";
          if (text) {
            options.onDelta?.(text);
          }
        } else if (parsedEvent.event === "complete") {
          completed = parsedEvent.data as SendChatMessageResult;
        } else if (parsedEvent.event === "error") {
          throw new ApiError(
            typeof parsedEvent.data.message === "string" ? parsedEvent.data.message : "Streaming chat failed.",
            typeof parsedEvent.data.status_code === "number" ? parsedEvent.data.status_code : 502,
            typeof parsedEvent.data.error === "string" ? parsedEvent.data.error : undefined,
          );
        }
      }
      boundaryIndex = buffer.indexOf("\n\n");
    }

    if (done) {
      break;
    }
  }

  if (!completed) {
    throw new ApiError("Streaming response ended before completion", 502, "stream_incomplete");
  }

  return completed;
}

function parseSseEvent(rawEvent: string): { event: string; data: Record<string, unknown> } | null {
  const normalized = rawEvent.replace(/\r/g, "");
  const lines = normalized.split("\n");
  let eventName = "message";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (!line || line.startsWith(":")) {
      continue;
    }
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim() || "message";
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  const payload = JSON.parse(dataLines.join("\n")) as Record<string, unknown>;
  return { event: eventName, data: payload };
}
