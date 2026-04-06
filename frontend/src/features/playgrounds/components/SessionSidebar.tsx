import { useEffect, useRef, useState } from "react";
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
  onRenameSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  canRenameSession: boolean;
  canDeleteSession: boolean;
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
  onRenameSession,
  onDeleteSession,
  canRenameSession,
  canDeleteSession,
}: SessionSidebarProps): JSX.Element {
  const [openMenuSessionId, setOpenMenuSessionId] = useState<string | null>(null);
  const sidebarRef = useRef<HTMLElement | null>(null);
  const historyToggleLabel = isCollapsed ? "Expand conversation history" : "Collapse conversation history";

  useEffect(() => {
    if (isCollapsed || isInteractionLocked) {
      setOpenMenuSessionId(null);
    }
  }, [isCollapsed, isInteractionLocked]);

  useEffect(() => {
    setOpenMenuSessionId(null);
  }, [activeSessionId]);

  useEffect(() => {
    if (!openMenuSessionId) {
      return;
    }

    const handlePointerDown = (event: MouseEvent): void => {
      if (sidebarRef.current && !sidebarRef.current.contains(event.target as Node)) {
        setOpenMenuSessionId(null);
      }
    };

    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        setOpenMenuSessionId(null);
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [openMenuSessionId]);

  return (
    <aside className="chatbot-sidebar" aria-label="Conversation history" data-collapsed={isCollapsed} ref={sidebarRef}>
      <div className="chatbot-sidebar-header">
        {!isCollapsed ? <h2 className="section-title">{title}</h2> : null}
        <div className="chatbot-sidebar-actions">
          <button
            type="button"
            className="chatbot-sidebar-toggle"
            aria-label={historyToggleLabel}
            title={historyToggleLabel}
            onClick={onToggleCollapsed}
          >
            <span className="chatbot-sidebar-toggle-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" focusable="false">
                <path d="M15.5 5.5 9 12l6.5 6.5-1.5 1.5L6 12l8-8 1.5 1.5Z" />
              </svg>
            </span>
          </button>
          <button
            type="button"
            className={isCollapsed ? "chatbot-sidebar-icon-button" : "btn btn-secondary"}
            onClick={onCreateSession}
            aria-label={isCollapsed ? newSessionLabel : undefined}
            title={isCollapsed ? newSessionLabel : undefined}
            disabled={!canCreateSession || isInteractionLocked}
          >
            {isCollapsed ? (
              <span className="chatbot-sidebar-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" focusable="false">
                  <path d="M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6V5Z" />
                </svg>
              </span>
            ) : newSessionLabel}
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
          {sessions.map((session) => {
            const actionsLabel = `Conversation actions for ${session.title}`;
            const isMenuOpen = openMenuSessionId === session.id;

            return (
              <div
                key={session.id}
                className={`chatbot-conversation-row ${session.id === activeSessionId ? "active" : ""}`}
                data-menu-open={isMenuOpen ? "true" : "false"}
              >
                <button
                  type="button"
                  className={`chatbot-conversation-item ${session.id === activeSessionId ? "active" : ""}`}
                  onClick={() => {
                    setOpenMenuSessionId(null);
                    onSelectSession(session.id);
                  }}
                  disabled={isInteractionLocked}
                  title={session.title}
                >
                  <strong className="chatbot-conversation-item-title" title={session.title}>{session.title}</strong>
                  <span className="chatbot-conversation-item-timestamp">{formatTimestamp(session.updatedAt)}</span>
                </button>
                {canRenameSession || canDeleteSession ? (
                  <div className="chatbot-conversation-item-actions">
                    <button
                      type="button"
                      className="chatbot-conversation-menu-trigger"
                      aria-label={actionsLabel}
                      title={actionsLabel}
                      aria-haspopup="menu"
                      aria-expanded={isMenuOpen}
                      onClick={(event) => {
                        event.stopPropagation();
                        setOpenMenuSessionId((current) => (current === session.id ? null : session.id));
                      }}
                      disabled={isInteractionLocked}
                    >
                      <span className="chatbot-sidebar-icon" aria-hidden="true">
                        <svg viewBox="0 0 24 24" focusable="false">
                          <path d="M12 7a1.75 1.75 0 1 1 0-3.5A1.75 1.75 0 0 1 12 7Zm0 6.75a1.75 1.75 0 1 1 0-3.5 1.75 1.75 0 0 1 0 3.5Zm0 6.75a1.75 1.75 0 1 1 0-3.5 1.75 1.75 0 0 1 0 3.5Z" />
                        </svg>
                      </span>
                    </button>
                    {isMenuOpen ? (
                      <div className="chatbot-conversation-menu" role="menu" aria-label={actionsLabel}>
                        {canRenameSession ? (
                          <button
                            type="button"
                            className="chatbot-conversation-menu-item"
                            role="menuitem"
                            onClick={() => {
                              setOpenMenuSessionId(null);
                              onRenameSession(session.id);
                            }}
                          >
                            Rename
                          </button>
                        ) : null}
                        {canDeleteSession ? (
                          <button
                            type="button"
                            className="chatbot-conversation-menu-item chatbot-conversation-menu-item-danger"
                            role="menuitem"
                            onClick={() => {
                              setOpenMenuSessionId(null);
                              onDeleteSession(session.id);
                            }}
                          >
                            Delete
                          </button>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : null}
    </aside>
  );
}
