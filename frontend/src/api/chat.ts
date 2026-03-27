import {
  createPlaygroundSession,
  deletePlaygroundSession,
  getPlaygroundSession,
  listPlaygroundSessions,
  streamPlaygroundMessage,
  updatePlaygroundSession,
  type PlaygroundMessage,
  type PlaygroundSessionDetail,
  type PlaygroundSessionSummary,
} from "./playgrounds";

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
  return (await listPlaygroundSessions("chat", token)).map(mapSummary);
}

export async function createChatConversation(
  payload: { model_id?: string | null } = {},
  token: string,
): Promise<ChatConversationDetail> {
  return mapDetail(await createPlaygroundSession(
    {
      playground_kind: "chat",
      model_selection: { model_id: payload.model_id ?? null },
    },
    token,
  ));
}

export async function getChatConversation(
  conversationId: string,
  token: string,
): Promise<ChatConversationDetail> {
  return mapDetail(await getPlaygroundSession(conversationId, "chat", token));
}

export async function updateChatConversation(
  conversationId: string,
  payload: { title?: string; model_id?: string | null },
  token: string,
): Promise<ChatConversationSummary> {
  return mapSummary(await updatePlaygroundSession(
    conversationId,
    {
      title: payload.title,
      model_selection: "model_id" in payload ? { model_id: payload.model_id ?? null } : undefined,
    },
    token,
  ));
}

export async function deleteChatConversation(
  conversationId: string,
  token: string,
): Promise<void> {
  await deletePlaygroundSession(conversationId, token);
}

export async function sendChatMessage(
  conversationId: string,
  payload: { prompt: string },
  token: string,
): Promise<SendChatMessageResult> {
  const result = await streamPlaygroundMessage(
    conversationId,
    payload,
    token,
  );
  return {
    conversation: mapSummary(result.session),
    messages: result.messages.map(mapMessage),
    output: result.output,
    response: result.response,
  };
}

export async function streamChatMessage(
  conversationId: string,
  payload: { prompt: string },
  token: string,
  options: StreamChatMessageOptions = {},
): Promise<SendChatMessageResult> {
  const result = await streamPlaygroundMessage(conversationId, payload, token, options);
  return {
    conversation: mapSummary(result.session),
    messages: result.messages.map(mapMessage),
    output: result.output,
    response: result.response,
  };
}

function mapSummary(session: PlaygroundSessionSummary): ChatConversationSummary {
  return {
    id: session.id,
    title: session.title,
    titleSource: session.title_source,
    modelId: session.model_selection.model_id,
    messageCount: session.message_count,
    createdAt: session.created_at,
    updatedAt: session.updated_at,
  };
}

function mapDetail(session: PlaygroundSessionDetail): ChatConversationDetail {
  return {
    ...mapSummary(session),
    messages: session.messages.map(mapMessage),
  };
}

function mapMessage(message: PlaygroundMessage): ChatConversationMessage {
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    metadata: message.metadata,
    createdAt: message.createdAt,
  };
}
