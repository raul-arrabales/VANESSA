import { useTranslation } from "react-i18next";
import type { PlaygroundConversationAction } from "../../../api/playgrounds";

type ConversationActionsProps = {
  messageId: string;
  actions: PlaygroundConversationAction[];
  activeActionKey: string | null;
  disabled: boolean;
  onAction: (messageId: string, action: PlaygroundConversationAction) => Promise<void>;
};

export default function ConversationActions({
  messageId,
  actions,
  activeActionKey,
  disabled,
  onAction,
}: ConversationActionsProps): JSX.Element | null {
  const { t } = useTranslation("common");
  if (actions.length === 0) {
    return null;
  }
  return (
    <div className="chatbot-conversation-actions" aria-label={t("playgrounds.messageActions.availableActions")}>
      {actions.map((action) => {
        const actionKey = `${messageId}:${action.id}`;
        const isActive = activeActionKey === actionKey;
        const executionLeaseExpired = action.state === "executing"
          && Boolean(action.executing_at)
          && Date.now() - Date.parse(action.executing_at as string) >= 120_000;
        const isInvokable = action.state === "enabled" || executionLeaseExpired;
        const isDisabled = !isInvokable || disabled || activeActionKey !== null;
        const knownLabel = action.label_key === "start_next_loop" || action.type === "start_workflow_cycle"
          ? t("playgrounds.messageActions.startNextLoop")
          : action.label;
        return (
          <button
            key={action.id}
            type="button"
            className={`btn ${action.emphasis === "primary" ? "btn-primary" : "btn-secondary"}`}
            disabled={isDisabled}
            aria-busy={isActive ? "true" : undefined}
            onClick={() => void onAction(messageId, action)}
          >
            {isActive
              ? t("playgrounds.messageActions.runningAction")
              : action.state === "consumed"
                ? t("playgrounds.messageActions.actionUsed")
                : knownLabel}
          </button>
        );
      })}
    </div>
  );
}
