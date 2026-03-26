import { ApiError } from "../auth/authApi";
import type { ChatHistoryItem } from "./modelops/types";

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
  knowledge_base_id?: string | null;
};

export type KnowledgeChatKnowledgeBaseOption = {
  id: string;
  display_name: string;
  slug?: string | null;
  index_name: string;
  is_default: boolean;
};

export type KnowledgeChatKnowledgeBaseOptions = {
  knowledge_bases: KnowledgeChatKnowledgeBaseOption[];
  default_knowledge_base_id?: string | null;
  selection_required: boolean;
  configuration_message?: string | null;
};

function buildUrl(path: string): string {
  return `${backendBaseUrl.replace(/\/$/, "")}${path}`;
}

export async function runKnowledgeChat(
  payload: {
    prompt: string;
    model: string;
    knowledge_base_id?: string | null;
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
  let parsed: Record<string, unknown> = {};
  if (rawBody) {
    try {
      parsed = JSON.parse(rawBody) as Record<string, unknown>;
    } catch {
      if (response.ok) {
        throw new Error("Knowledge chat returned an invalid response.");
      }
    }
  }

  if (!response.ok) {
    const message = rawBody && Object.keys(parsed).length > 0
      ? String(parsed.message ?? parsed.error ?? `HTTP ${response.status}`)
      : `Knowledge chat request failed: HTTP ${response.status}`;
    const code = parsed.error ? String(parsed.error) : undefined;
    throw new ApiError(message, response.status, code);
  }

  return parsed as unknown as KnowledgeChatResult;
}

export async function listKnowledgeChatKnowledgeBases(token: string): Promise<KnowledgeChatKnowledgeBaseOptions> {
  const response = await fetch(buildUrl("/v1/chat/knowledge/bases"), {
    method: "GET",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
  });
  const rawBody = await response.text();
  let parsed: Record<string, unknown> = {};
  if (rawBody) {
    try {
      parsed = JSON.parse(rawBody) as Record<string, unknown>;
    } catch {
      if (response.ok) {
        throw new Error("Knowledge chat configuration returned an invalid response.");
      }
    }
  }
  if (!response.ok) {
    const message = rawBody && Object.keys(parsed).length > 0
      ? String(parsed.message ?? parsed.error ?? `HTTP ${response.status}`)
      : `Knowledge chat configuration failed: HTTP ${response.status}`;
    const code = parsed.error ? String(parsed.error) : undefined;
    throw new ApiError(message, response.status, code);
  }
  return parsed as unknown as KnowledgeChatKnowledgeBaseOptions;
}
