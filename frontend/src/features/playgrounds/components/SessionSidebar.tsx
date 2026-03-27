import type { PlaygroundSessionViewModel } from "../types";
import { formatTimestamp } from "../utils";

type SessionSidebarProps = {
  title: string;
  introText: string;
  newSessionLabel: string;
  sessions: PlaygroundSessionViewModel[];
  activeSessionId: string | null;
  canCreateSession: boolean;
  isInteractionLocked: boolean;
  isCollapsed: boolean;
  onToggleCollapsed: () => void;
  onCreateSession: () => void;
  onSelectSession: (sessionId: string) => void;
};

export default function SessionSidebar({
  title,
  introText,
  newSessionLabel,
  sessions,
  activeSessionId,
  canCreateSession,
  isInteractionLocked,
  isCollapsed,
  onToggleCollapsed,
  onCreateSession,
  onSelectSession,
}: SessionSidebarProps): JSX.Element {
  return (
    <aside className="chatbot-sidebar" aria-label="Conversation history" data-collapsed={isCollapsed}>
      <div className="chatbot-sidebar-header">
        <h2 className="section-title">{title}</h2>
        <div className="chatbot-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onToggleCollapsed}
          >
            {isCollapsed ? "Show history" : "Hide history"}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onCreateSession}
            disabled={!canCreateSession || isInteractionLocked}
          >
            {newSessionLabel}
          </button>
        </div>
      </div>
      {!isCollapsed ? <p className="status-text">{introText}</p> : null}
      {!isCollapsed ? (
        <div className="chatbot-conversation-list" role="list">
          {sessions.map((session) => (
            <button
              key={session.id}
              type="button"
              className={`chatbot-conversation-item ${session.id === activeSessionId ? "active" : ""}`}
              onClick={() => onSelectSession(session.id)}
              disabled={isInteractionLocked}
            >
              <strong>{session.title}</strong>
              <span>{formatTimestamp(session.updatedAt)}</span>
            </button>
          ))}
        </div>
      ) : null}
    </aside>
  );
}
