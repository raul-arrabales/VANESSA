import { ApiError } from "../auth/authApi";
import type { ChatHistoryItem } from "./models";

const backendBaseUrl = (import.meta.env.VITE_BACKEND_BASE_URL as string | undefined)?.trim() || "/api";

export type KnowledgeSource = {
  id: string;
  title: string;
  snippet: string;
  uri?: string | null;
  source_type?: string | null;
  metadata: Record<string, unknown>;
  score?: number | null;
  score_kind?: string | null;
};

export type KnowledgeChatResult = {
  output: string;
  response?: Record<string, unknown>;
  sources: KnowledgeSource[];
  retrieval: {
    index: string;
    result_count: number;
  };
};

function buildUrl(path: string): string {
  return `${backendBaseUrl.replace(/\/$/, "")}${path}`;
}

export async function runKnowledgeChat(
  payload: {
    prompt: string;
    model: string;
    history?: ChatHistoryItem[];
  },
  token: string,
): Promise<KnowledgeChatResult> {
  const response = await fetch(buildUrl("/v1/chat/knowledge"), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  const rawBody = await response.text();
  const parsed = rawBody ? JSON.parse(rawBody) as Record<string, unknown> : {};

  if (!response.ok) {
    const message = String(parsed.message ?? parsed.error ?? `HTTP ${response.status}`);
    const code = parsed.error ? String(parsed.error) : undefined;
    throw new ApiError(message, response.status, code);
  }

  return parsed as unknown as KnowledgeChatResult;
}
