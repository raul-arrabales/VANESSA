import { useTranslation } from "react-i18next";
import { useSessionSidebarMenu } from "../hooks/useSessionSidebarMenu";
import type { PlaygroundSessionViewModel } from "../types";
import { formatTimestamp } from "../utils";

type SessionSidebarProps = {
  title: string;
  introText: string;
  historyLoadingText: string;
  newSessionLabel: string;
  temporarySessionLabel: string;
  settingsLabel: string;
  showSettings: boolean;
  sessions: PlaygroundSessionViewModel[];
  activeSessionId: string | null;
  canCreateSession: boolean;
  isInteractionLocked: boolean;
  isCollapsed: boolean;
  isHistoryLoading: boolean;
  historyError: string;
  onToggleCollapsed: () => void;
  onCreateSession: () => void;
  onCreateTemporarySession: () => void;
  onOpenSettings: () => void;
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
  temporarySessionLabel,
  settingsLabel,
  showSettings,
  sessions,
  activeSessionId,
  canCreateSession,
  isInteractionLocked,
  isCollapsed,
  isHistoryLoading,
  historyError,
  onToggleCollapsed,
  onCreateSession,
  onCreateTemporarySession,
  onOpenSettings,
  onSelectSession,
  onRenameSession,
  onDeleteSession,
  canRenameSession,
  canDeleteSession,
}: SessionSidebarProps): JSX.Element {
  const { t } = useTranslation("common");
  const {
    sidebarRef,
    isMenuOpen,
    toggleMenu,
    closeMenu,
  } = useSessionSidebarMenu({
    isCollapsed,
    isInteractionLocked,
    activeSessionId,
  });
  const historyToggleLabel = isCollapsed
    ? t("playgroundSessionSidebar.expand")
    : t("playgroundSessionSidebar.collapse");

  return (
    <aside
      className="chatbot-sidebar"
      aria-label={t("playgroundSessionSidebar.aria")}
      data-collapsed={isCollapsed}
      ref={sidebarRef}
    >
      <div className="chatbot-sidebar-header">
        <div className="chatbot-sidebar-title-row">
          {!isCollapsed ? <h2 className="section-title">{title}</h2> : null}
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
        </div>
        <div className="chatbot-sidebar-actions">
          <button
            type="button"
            className="chatbot-sidebar-icon-button"
            onClick={onCreateSession}
            aria-label={newSessionLabel}
            title={newSessionLabel}
            disabled={!canCreateSession || isInteractionLocked}
          >
            <span className="chatbot-sidebar-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" focusable="false">
                <path d="M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6V5Z" />
              </svg>
            </span>
          </button>
          <button
            type="button"
            className="chatbot-sidebar-icon-button chatbot-sidebar-temporary-button"
            onClick={onCreateTemporarySession}
            aria-label={temporarySessionLabel}
            title={temporarySessionLabel}
            disabled={!canCreateSession || isInteractionLocked}
          >
            <span className="chatbot-sidebar-icon chatbot-sidebar-icon-outline" aria-hidden="true">
              <svg viewBox="0 0 24 24" focusable="false">
                <path d="M6.5 5.5h11A2.5 2.5 0 0 1 20 8v6.5a2.5 2.5 0 0 1-2.5 2.5h-5.2L8 20v-3H6.5A2.5 2.5 0 0 1 4 14.5V8a2.5 2.5 0 0 1 2.5-2.5Z" />
              </svg>
            </span>
          </button>
          {showSettings ? (
            <button
              type="button"
              className="chatbot-sidebar-icon-button"
              onClick={onOpenSettings}
              aria-label={settingsLabel}
              title={settingsLabel}
            >
              <span className="chatbot-sidebar-icon chatbot-sidebar-icon-stroke" aria-hidden="true">
                <svg viewBox="0 0 24 24" focusable="false">
                  <path d="M19.4 15a7.9 7.9 0 0 0 .06-1 7.9 7.9 0 0 0-.06-1l2.1-1.65-2-3.46-2.48 1a7.7 7.7 0 0 0-1.73-1L14.9 5.25h-4l-.39 2.64a7.7 7.7 0 0 0-1.73 1l-2.48-1-2 3.46L6.4 13a7.9 7.9 0 0 0-.06 1 7.9 7.9 0 0 0 .06 1l-2.1 1.65 2 3.46 2.48-1a7.7 7.7 0 0 0 1.73 1l.39 2.64h4l.39-2.64a7.7 7.7 0 0 0 1.73-1l2.48 1 2-3.46L19.4 15Z" />
                </svg>
              </span>
            </button>
          ) : null}
        </div>
      </div>
      {!isCollapsed ? <p className="status-text chatbot-sidebar-intro">{introText}</p> : null}
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
            const actionsLabel = t("playgroundSessionSidebar.actionsFor", { title: session.title });
            const rowMenuOpen = isMenuOpen(session.id);

            return (
              <div
                key={session.id}
                className={`chatbot-conversation-row ${session.id === activeSessionId ? "active" : ""}`}
                data-menu-open={rowMenuOpen ? "true" : "false"}
              >
                <button
                  type="button"
                  className={`chatbot-conversation-item ${session.id === activeSessionId ? "active" : ""}`}
                  onClick={() => {
                    closeMenu();
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
                      aria-expanded={rowMenuOpen}
                      onClick={(event) => {
                        event.stopPropagation();
                        toggleMenu(session.id);
                      }}
                      disabled={isInteractionLocked}
                    >
                      <span className="chatbot-sidebar-icon" aria-hidden="true">
                        <svg viewBox="0 0 24 24" focusable="false">
                          <path d="M12 7a1.75 1.75 0 1 1 0-3.5A1.75 1.75 0 0 1 12 7Zm0 6.75a1.75 1.75 0 1 1 0-3.5 1.75 1.75 0 0 1 0 3.5Zm0 6.75a1.75 1.75 0 1 1 0-3.5 1.75 1.75 0 0 1 0 3.5Z" />
                        </svg>
                      </span>
                    </button>
                    {rowMenuOpen ? (
                      <div className="chatbot-conversation-menu" role="menu" aria-label={actionsLabel}>
                        {canRenameSession ? (
                          <button
                            type="button"
                            className="chatbot-conversation-menu-item"
                            role="menuitem"
                            onClick={() => {
                              closeMenu();
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
                              closeMenu();
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
