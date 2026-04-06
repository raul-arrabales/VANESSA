import type { PlaygroundSessionViewModel } from "../types";
import { formatTimestamp } from "../utils";

type SessionSidebarProps = {
  title: string;
  introText: string;
  historyLoadingText: string;
  newSessionLabel: string;
  sessions: PlaygroundSessionViewModel[];
  activeSessionId: string | null;
  canCreateSession: boolean;
  isInteractionLocked: boolean;
  isCollapsed: boolean;
  isHistoryLoading: boolean;
  historyError: string;
  onToggleCollapsed: () => void;
  onCreateSession: () => void;
  onSelectSession: (sessionId: string) => void;
};

export default function SessionSidebar({
  title,
  introText,
  historyLoadingText,
  newSessionLabel,
  sessions,
  activeSessionId,
  canCreateSession,
  isInteractionLocked,
  isCollapsed,
  isHistoryLoading,
  historyError,
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
          {isHistoryLoading ? (
            <div className="chatbot-history-loading" role="status" aria-live="polite">
              <span className="chatbot-history-loading-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" focusable="false">
                  <path d="M12 3a9 9 0 1 0 8.49 12H18.4a7 7 0 1 1-1.55-7.31L14 10h7V3l-2.72 2.72A8.96 8.96 0 0 0 12 3Z" />
                </svg>
              </span>
              <span className="status-text">{historyLoadingText}</span>
            </div>
          ) : null}
          {!isHistoryLoading && historyError ? (
            <p className="status-text error-text">{historyError}</p>
          ) : null}
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
