import { useTranslation } from "react-i18next";

type SessionSidebarHeaderProps = {
  title: string;
  newSessionLabel: string;
  temporarySessionLabel: string;
  settingsLabel: string;
  showSettings: boolean;
  canCreateSession: boolean;
  isInteractionLocked: boolean;
  isCollapsed: boolean;
  onToggleCollapsed: () => void;
  onCreateSession: () => void;
  onCreateTemporarySession: () => void;
  onOpenSettings: () => void;
};

export default function SessionSidebarHeader({
  title,
  newSessionLabel,
  temporarySessionLabel,
  settingsLabel,
  showSettings,
  canCreateSession,
  isInteractionLocked,
  isCollapsed,
  onToggleCollapsed,
  onCreateSession,
  onCreateTemporarySession,
  onOpenSettings,
}: SessionSidebarHeaderProps): JSX.Element {
  const { t } = useTranslation("common");
  const historyToggleLabel = isCollapsed
    ? t("playgroundSessionSidebar.expand")
    : t("playgroundSessionSidebar.collapse");

  return (
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
  );
}
