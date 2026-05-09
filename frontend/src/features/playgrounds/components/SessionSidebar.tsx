import { useTranslation } from "react-i18next";
import { useSessionSidebarMenu } from "../hooks/useSessionSidebarMenu";
import type { PlaygroundSessionFilters, PlaygroundSessionViewModel } from "../types";
import { formatTimestamp } from "../utils";
import SessionSidebarHeader from "./SessionSidebarHeader";

type SessionSidebarProps = {
  title: string;
  introText: string;
  historyLoadingText: string;
  newSessionLabel: string;
  temporarySessionLabel: string;
  settingsLabel: string;
  showSettings: boolean;
  isSearchOpen: boolean;
  searchFilters: PlaygroundSessionFilters;
  isSearchActive: boolean;
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
  onToggleSearch: () => void;
  onSearchFiltersChange: (filters: PlaygroundSessionFilters) => void;
  onClearSearch: () => void;
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
  isSearchOpen,
  searchFilters,
  isSearchActive,
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
  onToggleSearch,
  onSearchFiltersChange,
  onClearSearch,
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

  return (
    <aside
      className="chatbot-sidebar"
      aria-label={t("playgroundSessionSidebar.aria")}
      data-collapsed={isCollapsed}
      ref={sidebarRef}
    >
      <SessionSidebarHeader
        title={title}
        newSessionLabel={newSessionLabel}
        temporarySessionLabel={temporarySessionLabel}
        settingsLabel={settingsLabel}
        showSettings={showSettings}
        canCreateSession={canCreateSession}
        isInteractionLocked={isInteractionLocked}
        isCollapsed={isCollapsed}
        onToggleCollapsed={onToggleCollapsed}
        onCreateSession={onCreateSession}
        onCreateTemporarySession={onCreateTemporarySession}
        onOpenSettings={onOpenSettings}
        onToggleSearch={onToggleSearch}
      />
      {!isCollapsed && isSearchOpen ? (
        <div className="chatbot-history-search" role="search" aria-label={t("playgroundSessionSidebar.searchAria")}>
          <label className="control-group">
            <span className="field-label">{t("playgroundSessionSidebar.searchTitleLabel")}</span>
            <input
              className="field-input"
              type="search"
              value={searchFilters.titleQuery ?? ""}
              placeholder={t("playgroundSessionSidebar.searchTitlePlaceholder")}
              onChange={(event) => onSearchFiltersChange({
                ...searchFilters,
                titleQuery: event.currentTarget.value,
              })}
              disabled={isInteractionLocked}
            />
          </label>
          <div className="chatbot-history-date-grid">
            <label className="control-group">
              <span className="field-label">{t("playgroundSessionSidebar.updatedFromLabel")}</span>
              <input
                className="field-input"
                type="date"
                value={searchFilters.updatedFrom ?? ""}
                onChange={(event) => onSearchFiltersChange({
                  ...searchFilters,
                  updatedFrom: event.currentTarget.value,
                })}
                disabled={isInteractionLocked}
              />
            </label>
            <label className="control-group">
              <span className="field-label">{t("playgroundSessionSidebar.updatedToLabel")}</span>
              <input
                className="field-input"
                type="date"
                value={searchFilters.updatedTo ?? ""}
                onChange={(event) => onSearchFiltersChange({
                  ...searchFilters,
                  updatedTo: event.currentTarget.value,
                })}
                disabled={isInteractionLocked}
              />
            </label>
          </div>
          {isSearchActive ? (
            <button
              type="button"
              className="btn btn-ghost chatbot-history-search-clear"
              onClick={onClearSearch}
              disabled={isInteractionLocked}
            >
              {t("playgroundSessionSidebar.clearSearch")}
            </button>
          ) : null}
        </div>
      ) : null}
      {!isCollapsed && introText ? <p className="status-text chatbot-sidebar-intro">{introText}</p> : null}
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
          {!isHistoryLoading && !historyError && isSearchActive && sessions.length === 0 ? (
            <p className="status-text chatbot-history-empty">{t("playgroundSessionSidebar.noSearchResults")}</p>
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
