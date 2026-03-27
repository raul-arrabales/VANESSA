import type { ChatHistoryItem } from "./modelops/types";
import {
  createPlaygroundSession,
  getPlaygroundOptions,
  sendPlaygroundMessage,
} from "./playgrounds";

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

export async function runKnowledgeChat(
  payload: {
    prompt: string;
    model: string;
    knowledge_base_id?: string | null;
    history?: ChatHistoryItem[];
  },
  token: string,
): Promise<KnowledgeChatResult> {
  const session = await createPlaygroundSession(
    {
      playground_kind: "knowledge",
      model_selection: { model_id: payload.model },
      knowledge_binding: { knowledge_base_id: payload.knowledge_base_id ?? null },
    },
    token,
  );
  const result = await sendPlaygroundMessage(
    session.id,
    { prompt: payload.prompt },
    token,
  );
  return {
    output: result.output,
    response: result.response,
    sources: (result.sources as KnowledgeSource[] | undefined) ?? [],
    retrieval: result.retrieval ?? { index: "knowledge_base", result_count: 0 },
    knowledge_base_id: result.session.knowledge_binding.knowledge_base_id,
  };
}

export async function listKnowledgeChatKnowledgeBases(token: string): Promise<KnowledgeChatKnowledgeBaseOptions> {
  const options = await getPlaygroundOptions(token);
  return {
    knowledge_bases: options.knowledge_bases,
    default_knowledge_base_id: options.default_knowledge_base_id,
    selection_required: options.selection_required,
    configuration_message: options.configuration_message,
  };
}
