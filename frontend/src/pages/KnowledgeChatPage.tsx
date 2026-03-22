import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { runKnowledgeChat, type KnowledgeSource } from "../api/knowledge";
import ChatMessageBody from "../components/ChatMessageBody";
import { listEnabledModels, type ChatHistoryItem, type ModelCatalogItem } from "../api/modelops";
import { useAuth } from "../auth/AuthProvider";

type ConversationMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  sources?: KnowledgeSource[];
};

type Conversation = {
  id: string;
  title: string;
  modelId: string;
  messages: ConversationMessage[];
  createdAt: string;
  updatedAt: string;
};

const CONTEXT_CHAR_BUDGET = 8000;
const MAX_CONTEXT_MESSAGES = 14;

function makeId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function newConversation(initialModelId: string): Conversation {
  const now = new Date().toISOString();
  return {
    id: makeId(),
    title: "New knowledge conversation",
    modelId: initialModelId,
    messages: [],
    createdAt: now,
    updatedAt: now,
  };
}

function buildContextMessages(messages: ConversationMessage[]): ChatHistoryItem[] {
  const reversed = [...messages].reverse();
  const selected: ConversationMessage[] = [];
  let runningChars = 0;

  for (const message of reversed) {
    const estimatedLength = message.content.length;
    if (selected.length >= MAX_CONTEXT_MESSAGES) {
      break;
    }
    if (runningChars + estimatedLength > CONTEXT_CHAR_BUDGET && selected.length > 0) {
      break;
    }
    selected.push(message);
    runningChars += estimatedLength;
  }

  return selected.reverse().map((message) => ({
    role: message.role,
    content: message.content,
  }));
}

export default function KnowledgeChatPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token, isAuthenticated, user } = useAuth();
  const [models, setModels] = useState<ModelCatalogItem[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [isSending, setIsSending] = useState(false);

  const storageKey = useMemo(() => {
    if (!user) {
      return "vanessa:knowledge-chat:anonymous";
    }
    return `vanessa:knowledge-chat:${user.id}`;
  }, [user]);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      return;
    }

    const loadModels = async (): Promise<void> => {
      try {
        const enabledModels = await listEnabledModels(token);
        setModels(Array.isArray(enabledModels) ? enabledModels : []);
      } catch (requestError) {
        setError(requestError instanceof Error ? requestError.message : t("knowledgeChat.states.modelsError"));
      }
    };

    void loadModels();
  }, [isAuthenticated, t, token]);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }

    try {
      const raw = window.localStorage.getItem(storageKey);
      if (!raw) {
        return;
      }
      const parsed = JSON.parse(raw) as Conversation[];
      if (!Array.isArray(parsed)) {
        return;
      }
      setConversations(parsed);
      setActiveConversationId(parsed[0]?.id ?? null);
    } catch {
      window.localStorage.removeItem(storageKey);
    }
  }, [isAuthenticated, storageKey]);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }
    window.localStorage.setItem(storageKey, JSON.stringify(conversations));
  }, [conversations, isAuthenticated, storageKey]);

  useEffect(() => {
    if (models.length === 0) {
      return;
    }

    if (conversations.length === 0) {
      const created = newConversation(models[0].id);
      setConversations([created]);
      setActiveConversationId(created.id);
      return;
    }

    setConversations((currentConversations) => currentConversations.map((conversation) => {
      if (!conversation.modelId) {
        return { ...conversation, modelId: models[0].id };
      }
      return conversation;
    }));
  }, [models, conversations.length]);

  const activeConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === activeConversationId) ?? null,
    [activeConversationId, conversations],
  );

  const canCreateConversation = useMemo(
    () => models.length > 0 && conversations.every((conversation) => conversation.messages.length > 0),
    [conversations, models.length],
  );

  const createConversation = (): void => {
    if (!canCreateConversation) {
      return;
    }
    const modelId = activeConversation?.modelId || models[0]?.id || "";
    const created = newConversation(modelId);
    setConversations((existing) => [created, ...existing]);
    setActiveConversationId(created.id);
    setError("");
    setDraft("");
  };

  const updateConversationModel = (conversationId: string, modelId: string): void => {
    setConversations((existing) => existing.map((conversation) => {
      if (conversation.id !== conversationId) {
        return conversation;
      }
      return {
        ...conversation,
        modelId,
        updatedAt: new Date().toISOString(),
      };
    }));
  };

  const sendPrompt = async (): Promise<void> => {
    if (!token || !activeConversation || !activeConversation.modelId || !draft.trim()) {
      return;
    }

    const trimmedDraft = draft.trim();
    const userMessage: ConversationMessage = {
      id: makeId(),
      role: "user",
      content: trimmedDraft,
      createdAt: new Date().toISOString(),
    };

    setError("");
    setIsSending(true);
    setDraft("");

    const updatedConversation: Conversation = {
      ...activeConversation,
      title: activeConversation.messages.length === 0
        ? trimmedDraft.slice(0, 64)
        : activeConversation.title,
      messages: [...activeConversation.messages, userMessage],
      updatedAt: new Date().toISOString(),
    };

    setConversations((existing) => existing.map((conversation) => (
      conversation.id === activeConversation.id ? updatedConversation : conversation
    )));

    try {
      const history = buildContextMessages(activeConversation.messages);
      const result = await runKnowledgeChat(
        {
          prompt: trimmedDraft,
          model: activeConversation.modelId,
          history,
        },
        token,
      );

      const assistantMessage: ConversationMessage = {
        id: makeId(),
        role: "assistant",
        content: result.output,
        createdAt: new Date().toISOString(),
        sources: result.sources,
      };

      setConversations((existing) => existing.map((conversation) => {
        if (conversation.id !== activeConversation.id) {
          return conversation;
        }
        return {
          ...conversation,
          messages: [...conversation.messages, assistantMessage],
          updatedAt: new Date().toISOString(),
        };
      }));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : t("knowledgeChat.states.requestError"));
    } finally {
      setIsSending(false);
    }
  };

  return (
    <section className="panel chatbot-shell" aria-label={t("knowledgeChat.aria.panel")}>
      <aside className="chatbot-sidebar" aria-label={t("knowledgeChat.aria.history")}>
        <div className="chatbot-sidebar-header">
          <h2 className="section-title">{t("knowledgeChat.title")}</h2>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={createConversation}
            disabled={!canCreateConversation}
          >
            {t("knowledgeChat.actions.newChat")}
          </button>
        </div>
        <p className="status-text">{t("knowledgeChat.description")}</p>
        <div className="chatbot-conversation-list" role="list">
          {conversations.map((conversation) => (
            <button
              key={conversation.id}
              type="button"
              className={`chatbot-conversation-item ${conversation.id === activeConversationId ? "active" : ""}`}
              onClick={() => setActiveConversationId(conversation.id)}
            >
              <strong>{conversation.title}</strong>
              <span>{new Date(conversation.updatedAt).toLocaleString()}</span>
            </button>
          ))}
        </div>
      </aside>

      <div className="chatbot-main card-stack">
        <label className="field-label" htmlFor="knowledge-model-picker">{t("knowledgeChat.fields.model")}</label>
        <select
          id="knowledge-model-picker"
          className="field-input"
          value={activeConversation?.modelId ?? ""}
          onChange={(event) => {
            if (activeConversation) {
              updateConversationModel(activeConversation.id, event.currentTarget.value);
            }
          }}
          disabled={models.length === 0 || !activeConversation}
        >
          {models.length === 0 && <option value="">{t("knowledgeChat.states.noModels")}</option>}
          {models.map((model) => (
            <option key={model.id} value={model.id}>{model.name}</option>
          ))}
        </select>

        <div className="chatbot-thread" aria-live="polite">
          {activeConversation?.messages.length
            ? activeConversation.messages.map((message) => (
              <article
                key={message.id}
                className={`chatbot-message chatbot-message-${message.role}`}
              >
                <p className="chatbot-message-role">
                  {message.role === "user" ? t("knowledgeChat.labels.you") : t("knowledgeChat.labels.assistant")}
                </p>
                <ChatMessageBody
                  content={message.content}
                  renderMarkdown={message.role === "assistant"}
                />
                {message.role === "assistant" && message.sources?.length
                  ? (
                    <section className="knowledge-chat-sources" aria-label={t("knowledgeChat.sources.title")}>
                      <p className="knowledge-chat-sources-title">{t("knowledgeChat.sources.title")}</p>
                      <div className="knowledge-chat-source-list">
                        {message.sources.map((source) => (
                          <article key={`${message.id}-${source.id}`} className="knowledge-chat-source">
                            <p className="knowledge-chat-source-title">
                              {source.uri
                                ? <a href={source.uri} target="_blank" rel="noreferrer">{source.title}</a>
                                : source.title}
                            </p>
                            <p className="knowledge-chat-source-snippet">{source.snippet}</p>
                          </article>
                        ))}
                      </div>
                    </section>
                  )
                  : null}
              </article>
            ))
            : <p className="status-text">{t("knowledgeChat.states.empty")}</p>}
        </div>

        <label className="field-label" htmlFor="knowledge-prompt">{t("knowledgeChat.fields.message")}</label>
        <textarea
          id="knowledge-prompt"
          className="field-input"
          value={draft}
          onChange={(event) => setDraft(event.currentTarget.value)}
          rows={4}
          placeholder={t("knowledgeChat.fields.placeholder")}
        />

        <button
          type="button"
          className="btn btn-primary"
          onClick={() => void sendPrompt()}
          disabled={!activeConversation?.modelId || !draft.trim() || isSending}
        >
          {isSending ? t("knowledgeChat.actions.sending") : t("knowledgeChat.actions.send")}
        </button>

        {error && <p className="status-text error-text">{error}</p>}
      </div>
    </section>
  );
}
