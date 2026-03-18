import { useEffect, useMemo, useState } from "react";
import {
  createChatConversation,
  deleteChatConversation,
  getChatConversation,
  listChatConversations,
  sendChatMessage,
  updateChatConversation,
  type ChatConversationDetail,
  type ChatConversationSummary,
} from "../api/chat";
import ChatMessageBody from "../components/ChatMessageBody";
import { listEnabledModels, type ModelCatalogItem } from "../api/models";
import { useAuth } from "../auth/AuthProvider";

function sortConversations(conversations: ChatConversationSummary[]): ChatConversationSummary[] {
  return [...conversations].sort((left, right) => {
    const leftTime = left.updatedAt ? Date.parse(left.updatedAt) : 0;
    const rightTime = right.updatedAt ? Date.parse(right.updatedAt) : 0;
    return rightTime - leftTime;
  });
}

function upsertConversationSummary(
  conversations: ChatConversationSummary[],
  nextConversation: ChatConversationSummary,
): ChatConversationSummary[] {
  const filtered = conversations.filter((conversation) => conversation.id !== nextConversation.id);
  return sortConversations([nextConversation, ...filtered]);
}

function removeConversationSummary(
  conversations: ChatConversationSummary[],
  conversationId: string,
): ChatConversationSummary[] {
  return conversations.filter((conversation) => conversation.id !== conversationId);
}

function formatTimestamp(value: string | null): string {
  if (!value) {
    return "";
  }
  return new Date(value).toLocaleString();
}

export default function ChatbotPage(): JSX.Element {
  const { token, isAuthenticated } = useAuth();
  const [models, setModels] = useState<ModelCatalogItem[]>([]);
  const [conversations, setConversations] = useState<ChatConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [activeConversation, setActiveConversation] = useState<ChatConversationDetail | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isBootstrapping, setIsBootstrapping] = useState(false);
  const [isConversationBusy, setIsConversationBusy] = useState(false);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      setModels([]);
      setConversations([]);
      setActiveConversationId(null);
      setActiveConversation(null);
      return;
    }

    const loadModels = async (): Promise<void> => {
      try {
        const enabledModels = await listEnabledModels(token);
        setModels(enabledModels);
      } catch (requestError) {
        setError(requestError instanceof Error ? requestError.message : "Unable to load models.");
      }
    };

    void loadModels();
  }, [isAuthenticated, token]);

  useEffect(() => {
    if (!isAuthenticated || !token || models.length === 0) {
      return;
    }

    let cancelled = false;

    const bootstrapConversations = async (): Promise<void> => {
      setIsBootstrapping(true);
      try {
        const listed = await listChatConversations(token);
        if (cancelled) {
          return;
        }
        if (listed.length === 0) {
          const created = await createChatConversation({ model_id: models[0]?.id ?? null }, token);
          if (cancelled) {
            return;
          }
          const { messages, ...summary } = created;
          setConversations([summary]);
          setActiveConversationId(created.id);
          setActiveConversation(created);
          return;
        }

        const sorted = sortConversations(listed);
        setConversations(sorted);
        setActiveConversationId((current) => (
          current && sorted.some((conversation) => conversation.id === current)
            ? current
            : sorted[0]?.id ?? null
        ));
      } catch (requestError) {
        if (!cancelled) {
          setError(requestError instanceof Error ? requestError.message : "Unable to load conversations.");
        }
      } finally {
        if (!cancelled) {
          setIsBootstrapping(false);
        }
      }
    };

    void bootstrapConversations();

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, models, token]);

  useEffect(() => {
    if (!isAuthenticated || !token || !activeConversationId) {
      setActiveConversation(null);
      return;
    }

    if (activeConversation?.id === activeConversationId) {
      return;
    }

    let cancelled = false;

    const loadConversation = async (): Promise<void> => {
      try {
        const conversation = await getChatConversation(activeConversationId, token);
        if (!cancelled) {
          setActiveConversation(conversation);
        }
      } catch (requestError) {
        if (!cancelled) {
          setError(requestError instanceof Error ? requestError.message : "Unable to load conversation.");
        }
      }
    };

    void loadConversation();

    return () => {
      cancelled = true;
    };
  }, [activeConversation?.id, activeConversationId, isAuthenticated, token]);

  const canCreateConversation = useMemo(
    () => models.length > 0 && conversations.every((conversation) => conversation.messageCount > 0),
    [conversations, models.length],
  );

  const activeConversationModelId = activeConversation?.modelId ?? "";

  const createConversation = async (): Promise<void> => {
    if (!token || !canCreateConversation) {
      return;
    }

    setError("");
    setIsConversationBusy(true);
    try {
      const created = await createChatConversation({ model_id: activeConversationModelId || models[0]?.id || null }, token);
      const { messages, ...summary } = created;
      setConversations((existing) => upsertConversationSummary(existing, summary));
      setActiveConversationId(created.id);
      setActiveConversation(created);
      setDraft("");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to create conversation.");
    } finally {
      setIsConversationBusy(false);
    }
  };

  const updateConversationModel = async (conversationId: string, modelId: string): Promise<void> => {
    if (!token) {
      return;
    }

    setError("");
    try {
      const updated = await updateChatConversation(conversationId, { model_id: modelId }, token);
      setConversations((existing) => upsertConversationSummary(existing, updated));
      setActiveConversation((current) => (
        current && current.id === conversationId ? { ...current, ...updated } : current
      ));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to update conversation model.");
    }
  };

  const renameConversation = async (): Promise<void> => {
    if (!token || !activeConversation) {
      return;
    }

    const nextTitle = window.prompt("Rename conversation", activeConversation.title);
    if (nextTitle === null) {
      return;
    }

    setError("");
    setIsConversationBusy(true);
    try {
      const updated = await updateChatConversation(activeConversation.id, { title: nextTitle }, token);
      setConversations((existing) => upsertConversationSummary(existing, updated));
      setActiveConversation((current) => (
        current && current.id === updated.id ? { ...current, ...updated } : current
      ));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to rename conversation.");
    } finally {
      setIsConversationBusy(false);
    }
  };

  const deleteConversation = async (): Promise<void> => {
    if (!token || !activeConversation) {
      return;
    }
    if (!window.confirm("Delete this conversation?")) {
      return;
    }

    setError("");
    setIsConversationBusy(true);
    try {
      await deleteChatConversation(activeConversation.id, token);
      const remaining = removeConversationSummary(conversations, activeConversation.id);
      if (remaining.length === 0) {
        const created = await createChatConversation({ model_id: models[0]?.id ?? null }, token);
        const { messages, ...summary } = created;
        setConversations([summary]);
        setActiveConversationId(created.id);
        setActiveConversation(created);
      } else {
        const sorted = sortConversations(remaining);
        setConversations(sorted);
        setActiveConversationId(sorted[0].id);
        setActiveConversation(null);
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to delete conversation.");
    } finally {
      setIsConversationBusy(false);
    }
  };

  const sendPrompt = async (): Promise<void> => {
    if (!token || !activeConversation || !activeConversation.modelId || !draft.trim()) {
      return;
    }

    const prompt = draft.trim();
    setError("");
    setIsSending(true);

    try {
      const result = await sendChatMessage(activeConversation.id, { prompt }, token);
      setConversations((existing) => upsertConversationSummary(existing, result.conversation));
      setActiveConversation((current) => {
        if (!current || current.id !== activeConversation.id) {
          return current;
        }
        return {
          ...current,
          ...result.conversation,
          messages: [...current.messages, ...result.messages],
        };
      });
      setDraft("");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Message request failed.");
    } finally {
      setIsSending(false);
    }
  };

  return (
    <section className="panel chatbot-shell" aria-label="Chat panel">
      <aside className="chatbot-sidebar" aria-label="Conversation history">
        <div className="chatbot-sidebar-header">
          <h2 className="section-title">Chat</h2>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => void createConversation()}
            disabled={!canCreateConversation || isConversationBusy}
          >
            New chat
          </button>
        </div>
        <p className="status-text">Choose a model and continue any prior conversation.</p>
        <div className="chatbot-conversation-list" role="list">
          {conversations.map((conversation) => (
            <button
              key={conversation.id}
              type="button"
              className={`chatbot-conversation-item ${conversation.id === activeConversationId ? "active" : ""}`}
              onClick={() => {
                setActiveConversationId(conversation.id);
                setActiveConversation(null);
              }}
            >
              <strong>{conversation.title}</strong>
              <span>{formatTimestamp(conversation.updatedAt)}</span>
            </button>
          ))}
        </div>
      </aside>

      <div className="chatbot-main card-stack">
        <div className="chatbot-sidebar-header">
          <h3 className="section-title">{activeConversation?.title ?? "New conversation"}</h3>
          <div className="chatbot-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => void renameConversation()}
              disabled={!activeConversation || isConversationBusy}
            >
              Rename
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => void deleteConversation()}
              disabled={!activeConversation || isConversationBusy}
            >
              Delete
            </button>
          </div>
        </div>

        <label className="field-label" htmlFor="model-picker">Model</label>
        <select
          id="model-picker"
          className="field-input"
          value={activeConversationModelId}
          onChange={(event) => {
            if (activeConversation) {
              void updateConversationModel(activeConversation.id, event.currentTarget.value);
            }
          }}
          disabled={models.length === 0 || !activeConversation}
        >
          {models.length === 0 && <option value="">No enabled models</option>}
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
                <p className="chatbot-message-role">{message.role === "user" ? "You" : "Assistant"}</p>
                <ChatMessageBody
                  content={message.content}
                  renderMarkdown={message.role === "assistant"}
                />
              </article>
            ))
            : <p className="status-text">
              {isBootstrapping ? "Loading conversations..." : "No messages yet. Start chatting to build context memory."}
            </p>}
        </div>

        <label className="field-label" htmlFor="prompt">Message</label>
        <textarea
          id="prompt"
          className="field-input"
          value={draft}
          onChange={(event) => setDraft(event.currentTarget.value)}
          rows={4}
          placeholder="Type your message"
        />

        <button
          type="button"
          className="btn btn-primary"
          onClick={() => void sendPrompt()}
          disabled={!activeConversation?.modelId || !draft.trim() || isSending}
        >
          {isSending ? "Sending..." : "Send"}
        </button>

        {error && <p className="status-text error-text">{error}</p>}
      </div>
    </section>
  );
}
