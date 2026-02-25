import { useEffect, useMemo, useState } from "react";
import {
  listEnabledModels,
  runInference,
  type ChatHistoryItem,
  type ModelCatalogItem,
} from "../api/models";
import { useAuth } from "../auth/AuthProvider";

type ConversationMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
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
    title: "New conversation",
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

export default function ChatbotPage(): JSX.Element {
  const { token, isAuthenticated, user } = useAuth();
  const [models, setModels] = useState<ModelCatalogItem[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [isSending, setIsSending] = useState(false);

  const storageKey = useMemo(() => {
    if (!user) {
      return "vanessa:chat:anonymous";
    }
    return `vanessa:chat:${user.id}`;
  }, [user]);

  useEffect(() => {
    if (!isAuthenticated || !token) {
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

    const userMessage: ConversationMessage = {
      id: makeId(),
      role: "user",
      content: draft.trim(),
      createdAt: new Date().toISOString(),
    };

    setError("");
    setIsSending(true);
    setDraft("");

    const updatedConversation: Conversation = {
      ...activeConversation,
      title: activeConversation.messages.length === 0
        ? userMessage.content.slice(0, 64)
        : activeConversation.title,
      messages: [...activeConversation.messages, userMessage],
      updatedAt: new Date().toISOString(),
    };

    setConversations((existing) => existing.map((conversation) => (
      conversation.id === activeConversation.id ? updatedConversation : conversation
    )));

    try {
      const context = buildContextMessages(updatedConversation.messages);
      const result = await runInference(
        userMessage.content,
        activeConversation.modelId,
        token,
        context,
      );

      const assistantMessage: ConversationMessage = {
        id: makeId(),
        role: "assistant",
        content: result.output,
        createdAt: new Date().toISOString(),
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
      setError(requestError instanceof Error ? requestError.message : "Inference request failed.");
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
            onClick={createConversation}
            disabled={!canCreateConversation}
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
              onClick={() => setActiveConversationId(conversation.id)}
            >
              <strong>{conversation.title}</strong>
              <span>{new Date(conversation.updatedAt).toLocaleString()}</span>
            </button>
          ))}
        </div>
      </aside>

      <div className="chatbot-main card-stack">
        <label className="field-label" htmlFor="model-picker">Model</label>
        <select
          id="model-picker"
          className="field-input"
          value={activeConversation?.modelId ?? ""}
          onChange={(event) => {
            if (activeConversation) {
              updateConversationModel(activeConversation.id, event.currentTarget.value);
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
                <p>{message.content}</p>
              </article>
            ))
            : <p className="status-text">No messages yet. Start chatting to build context memory.</p>}
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
