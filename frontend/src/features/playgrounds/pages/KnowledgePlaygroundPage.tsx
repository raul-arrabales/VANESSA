import { useEffect, useMemo, useState } from "react";
import ChatMessageBody from "../../../components/ChatMessageBody";
import { useAuth } from "../../../auth/AuthProvider";
import {
  createPlaygroundSession,
  getPlaygroundOptions,
  getPlaygroundSession,
  listPlaygroundSessions,
  sendPlaygroundMessage,
  updatePlaygroundSession,
  type PlaygroundKnowledgeBaseOption,
  type PlaygroundSessionDetail,
  type PlaygroundSessionSummary,
} from "../../../api/playgrounds";

function formatTimestamp(value: string | null): string {
  if (!value) {
    return "";
  }
  return new Date(value).toLocaleString();
}

function upsertSession(
  sessions: PlaygroundSessionSummary[],
  nextSession: PlaygroundSessionSummary,
): PlaygroundSessionSummary[] {
  const filtered = sessions.filter((item) => item.id !== nextSession.id);
  return [nextSession, ...filtered].sort((left, right) => {
    const leftTime = left.updated_at ? Date.parse(left.updated_at) : 0;
    const rightTime = right.updated_at ? Date.parse(right.updated_at) : 0;
    return rightTime - leftTime;
  });
}

export default function KnowledgePlaygroundPage(): JSX.Element {
  const { token, isAuthenticated } = useAuth();
  const [sessions, setSessions] = useState<PlaygroundSessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeSession, setActiveSession] = useState<PlaygroundSessionDetail | null>(null);
  const [models, setModels] = useState<Array<{ id: string; display_name: string }>>([]);
  const [knowledgeBases, setKnowledgeBases] = useState<PlaygroundKnowledgeBaseOption[]>([]);
  const [defaultKnowledgeBaseId, setDefaultKnowledgeBaseId] = useState<string | null>(null);
  const [configurationMessage, setConfigurationMessage] = useState("");
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      setSessions([]);
      setActiveSessionId(null);
      setActiveSession(null);
      return;
    }

    let cancelled = false;
    const load = async (): Promise<void> => {
      try {
        const options = await getPlaygroundOptions(token);
        if (cancelled) {
          return;
        }
        setModels(options.models);
        setKnowledgeBases(options.knowledge_bases);
        setDefaultKnowledgeBaseId(options.default_knowledge_base_id ?? null);
        setConfigurationMessage(options.configuration_message ?? "");

        const existing = await listPlaygroundSessions("knowledge", token);
        if (cancelled) {
          return;
        }
        if (existing.length === 0) {
          const created = await createPlaygroundSession(
            {
              playground_kind: "knowledge",
              model_selection: { model_id: options.models[0]?.id ?? null },
              knowledge_binding: { knowledge_base_id: options.default_knowledge_base_id ?? options.knowledge_bases[0]?.id ?? null },
            },
            token,
          );
          if (cancelled) {
            return;
          }
          const { messages, ...summary } = created;
          setSessions([summary]);
          setActiveSessionId(created.id);
          setActiveSession(created);
          return;
        }

        setSessions(existing);
        setActiveSessionId(existing[0]?.id ?? null);
      } catch (requestError) {
        if (!cancelled) {
          setError(requestError instanceof Error ? requestError.message : "Unable to load knowledge playground.");
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, token]);

  useEffect(() => {
    if (!token || !activeSessionId) {
      setActiveSession(null);
      return;
    }
    let cancelled = false;
    const load = async (): Promise<void> => {
      try {
        const session = await getPlaygroundSession(activeSessionId, "knowledge", token);
        if (!cancelled) {
          setActiveSession(session);
        }
      } catch (requestError) {
        if (!cancelled) {
          setError(requestError instanceof Error ? requestError.message : "Unable to load knowledge session.");
        }
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [activeSessionId, token]);

  const canCreateConversation = useMemo(
    () => models.length > 0 && sessions.every((session) => session.message_count > 0),
    [models.length, sessions],
  );

  const createSession = async (): Promise<void> => {
    if (!token || !canCreateConversation) {
      return;
    }
    const created = await createPlaygroundSession(
      {
        playground_kind: "knowledge",
        model_selection: { model_id: activeSession?.model_selection.model_id ?? models[0]?.id ?? null },
        knowledge_binding: {
          knowledge_base_id: activeSession?.knowledge_binding.knowledge_base_id ?? defaultKnowledgeBaseId ?? knowledgeBases[0]?.id ?? null,
        },
      },
      token,
    );
    const { messages, ...summary } = created;
    setSessions((current) => upsertSession(current, summary));
    setActiveSessionId(created.id);
    setActiveSession(created);
    setDraft("");
  };

  const updateModel = async (sessionId: string, modelId: string): Promise<void> => {
    if (!token) {
      return;
    }
    const updated = await updatePlaygroundSession(
      sessionId,
      { model_selection: { model_id: modelId } },
      token,
    );
    setSessions((current) => upsertSession(current, updated));
    setActiveSession((current) => (
      current && current.id === sessionId
        ? { ...current, ...updated, messages: current.messages }
        : current
    ));
  };

  const updateKnowledgeBase = async (sessionId: string, knowledgeBaseId: string): Promise<void> => {
    if (!token) {
      return;
    }
    const updated = await updatePlaygroundSession(
      sessionId,
      { knowledge_binding: { knowledge_base_id: knowledgeBaseId } },
      token,
    );
    setSessions((current) => upsertSession(current, updated));
    setActiveSession((current) => (
      current && current.id === sessionId
        ? { ...current, ...updated, messages: current.messages }
        : current
    ));
  };

  const sendPrompt = async (): Promise<void> => {
    if (!token || !activeSession || !draft.trim()) {
      return;
    }
    if (!activeSession.model_selection.model_id) {
      setError("Model is required.");
      return;
    }
    if (!activeSession.knowledge_binding.knowledge_base_id) {
      setError(configurationMessage || "Knowledge base is required.");
      return;
    }
    setIsSending(true);
    setError("");
    try {
      const result = await sendPlaygroundMessage(
        activeSession.id,
        { prompt: draft.trim() },
        token,
      );
      const { messages, ...summary } = result.session;
      setSessions((current) => upsertSession(current, summary));
      setActiveSession(result.session);
      setDraft("");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to run knowledge chat.");
    } finally {
      setIsSending(false);
    }
  };

  const activeModelId = activeSession?.model_selection.model_id ?? "";
  const activeKnowledgeBaseId = activeSession?.knowledge_binding.knowledge_base_id ?? "";

  return (
    <section className="panel card-stack">
      <div className="chatbot-layout">
        <aside className="chatbot-sidebar">
          <div className="chatbot-sidebar-header">
            <h2 className="section-title">Knowledge playground</h2>
            <button type="button" className="secondary-button" onClick={() => void createSession()} disabled={!canCreateConversation}>
              New knowledge chat
            </button>
          </div>
          <div className="chatbot-conversation-list" role="list">
            {sessions.map((session) => (
              <button
                key={session.id}
                type="button"
                className={`chatbot-conversation-button${session.id === activeSessionId ? " is-active" : ""}`}
                onClick={() => setActiveSessionId(session.id)}
              >
                <span>{session.title}</span>
                <span className="status-text">{formatTimestamp(session.updated_at)}</span>
              </button>
            ))}
          </div>
        </aside>
        <div className="chatbot-main">
          <header className="chatbot-header">
            <div>
              <h3>{activeSession?.title ?? "Knowledge playground"}</h3>
              <p className="status-text">{activeSession ? `${activeSession.message_count} messages` : "No active session"}</p>
            </div>
            <div className="chatbot-toolbar">
              <label>
                Model
                <select
                  aria-label="Model"
                  value={activeModelId}
                  onChange={(event) => {
                    if (activeSession) {
                      void updateModel(activeSession.id, event.currentTarget.value);
                    }
                  }}
                >
                  {models.map((model) => (
                    <option key={model.id} value={model.id}>{model.display_name}</option>
                  ))}
                </select>
              </label>
              <label>
                Knowledge base
                <select
                  aria-label="Knowledge base"
                  value={activeKnowledgeBaseId}
                  onChange={(event) => {
                    if (activeSession) {
                      void updateKnowledgeBase(activeSession.id, event.currentTarget.value);
                    }
                  }}
                >
                  {knowledgeBases.map((knowledgeBase) => (
                    <option key={knowledgeBase.id} value={knowledgeBase.id}>{knowledgeBase.display_name}</option>
                  ))}
                </select>
              </label>
            </div>
          </header>

          <div className="chatbot-thread">
            {activeSession?.messages.map((message) => {
              const sources = Array.isArray(message.metadata.sources) ? message.metadata.sources as Array<Record<string, unknown>> : [];
              return (
                <article key={message.id} className={`chatbot-message ${message.role === "assistant" ? "chatbot-message-assistant" : "chatbot-message-user"}`}>
                  <ChatMessageBody content={message.content} renderMarkdown={message.role === "assistant"} />
                  {message.role === "assistant" && sources.length > 0 ? (
                    <div className="card-stack">
                      {sources.map((source) => (
                        <div key={String(source.id ?? source.title ?? Math.random())} className="panel">
                          <strong>{String(source.title ?? source.id ?? "Source")}</strong>
                          <p>{String(source.snippet ?? "")}</p>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </article>
              );
            })}
          </div>

          <div className="chatbot-composer">
            <label>
              Message
              <textarea
                aria-label="Message"
                value={draft}
                onChange={(event) => setDraft(event.currentTarget.value)}
              />
            </label>
            <div className="chatbot-actions">
              <button type="button" className="primary-button" onClick={() => void sendPrompt()} disabled={isSending}>
                {isSending ? "Asking..." : "Ask knowledge chat"}
              </button>
            </div>
            {error ? <p className="status-text">{error}</p> : null}
          </div>
        </div>
      </div>
    </section>
  );
}
