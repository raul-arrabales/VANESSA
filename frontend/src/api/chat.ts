import { requestJson } from "../auth/authApi";

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
