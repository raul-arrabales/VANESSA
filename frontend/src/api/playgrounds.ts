import { ApiError, buildUrl, requestJson } from "../auth/authApi";

export type PlaygroundKind = "chat" | "knowledge";

export type PlaygroundMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  metadata: Record<string, unknown>;
  createdAt: string | null;
};

export type PlaygroundSessionSummary = {
  id: string;
  playground_kind: PlaygroundKind;
  assistant_ref: string;
  title: string;
  title_source: "auto" | "manual";
  model_selection: {
    model_id: string | null;
  };
  knowledge_binding: {
    knowledge_base_id: string | null;
  };
  message_count: number;
  created_at: string | null;
  updated_at: string | null;
};

export type PlaygroundSessionDetail = PlaygroundSessionSummary & {
  messages: PlaygroundMessage[];
};

export type PlaygroundAssistantOption = {
  assistant_ref: string;
  display_name: string;
  description: string;
  playground_kind: PlaygroundKind;
  agent_id?: string | null;
  knowledge_required?: boolean;
};

export type PlaygroundKnowledgeBaseOption = {
  id: string;
  display_name: string;
  slug?: string | null;
  index_name: string;
  is_default: boolean;
};

export type PlaygroundOptions = {
  assistants: PlaygroundAssistantOption[];
  models: Array<{
    id: string;
    display_name: string;
    task_key?: string | null;
  }>;
  knowledge_bases: PlaygroundKnowledgeBaseOption[];
  default_knowledge_base_id?: string | null;
  selection_required: boolean;
  configuration_message?: string | null;
};

export type SendPlaygroundMessageResult = {
  session: PlaygroundSessionDetail;
  messages: PlaygroundMessage[];
  output: string;
  response?: Record<string, unknown>;
  sources?: Array<Record<string, unknown>>;
  retrieval?: {
    index: string;
    result_count: number;
  };
};

export type StreamPlaygroundMessageOptions = {
  onDelta?: (text: string) => void;
  signal?: AbortSignal;
};

export async function listPlaygroundSessions(
  playgroundKind: PlaygroundKind,
  token: string,
): Promise<PlaygroundSessionSummary[]> {
  const result = await requestJson<{ sessions: PlaygroundSessionSummary[] }>(
    `/v1/playgrounds/sessions?playground_kind=${encodeURIComponent(playgroundKind)}`,
    { token },
  );
  return result.sessions;
}

export async function createPlaygroundSession(
  payload: {
    playground_kind: PlaygroundKind;
    assistant_ref?: string;
    model_selection?: { model_id?: string | null };
    knowledge_binding?: { knowledge_base_id?: string | null };
  },
  token: string,
): Promise<PlaygroundSessionDetail> {
  const result = await requestJson<{ session: PlaygroundSessionDetail }>("/v1/playgrounds/sessions", {
    method: "POST",
    token,
    body: payload,
  });
  return result.session;
}

export async function getPlaygroundSession(
  sessionId: string,
  playgroundKind: PlaygroundKind,
  token: string,
): Promise<PlaygroundSessionDetail> {
  const result = await requestJson<{ session: PlaygroundSessionDetail }>(
    `/v1/playgrounds/sessions/${encodeURIComponent(sessionId)}?playground_kind=${encodeURIComponent(playgroundKind)}`,
    { token },
  );
  return result.session;
}

export async function updatePlaygroundSession(
  sessionId: string,
  payload: {
    title?: string;
    assistant_ref?: string;
    model_selection?: { model_id?: string | null };
    knowledge_binding?: { knowledge_base_id?: string | null };
  },
  token: string,
): Promise<PlaygroundSessionSummary> {
  const result = await requestJson<{ session: PlaygroundSessionSummary }>(
    `/v1/playgrounds/sessions/${encodeURIComponent(sessionId)}`,
    {
      method: "PATCH",
      token,
      body: payload,
    },
  );
  return result.session;
}

export async function deletePlaygroundSession(sessionId: string, token: string): Promise<void> {
  await requestJson<{ deleted: boolean }>(`/v1/playgrounds/sessions/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
    token,
  });
}

export async function sendPlaygroundMessage(
  sessionId: string,
  payload: { prompt: string },
  token: string,
): Promise<SendPlaygroundMessageResult> {
  return requestJson<SendPlaygroundMessageResult>(
    `/v1/playgrounds/sessions/${encodeURIComponent(sessionId)}/messages`,
    {
      method: "POST",
      token,
      body: payload,
    },
  );
}

export async function streamPlaygroundMessage(
  sessionId: string,
  payload: { prompt: string },
  token: string,
  options: StreamPlaygroundMessageOptions = {},
): Promise<SendPlaygroundMessageResult> {
  const response = await fetch(
    buildUrl(`/v1/playgrounds/sessions/${encodeURIComponent(sessionId)}/messages/stream`),
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
  let completed: SendPlaygroundMessageResult | null = null;

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
          completed = parsedEvent.data as SendPlaygroundMessageResult;
        } else if (parsedEvent.event === "error") {
          throw new ApiError(
            typeof parsedEvent.data.message === "string" ? parsedEvent.data.message : "Streaming playground failed.",
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

export async function getPlaygroundOptions(token: string): Promise<PlaygroundOptions> {
  return requestJson<PlaygroundOptions>("/v1/playgrounds/options", { token });
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
