import { useEffect, useRef, useState, type CSSProperties, type ReactNode, type RefObject } from "react";
import { useTranslation } from "react-i18next";
import ChatMessageBody from "../../../components/ChatMessageBody";
import { useActionFeedback } from "../../../feedback/ActionFeedbackProvider";
import { getPlaygroundMessageReferences, getPlaygroundMessageSources } from "../../../api/playgrounds";
import KnowledgeReferencesList from "../../ai-shared/KnowledgeReferencesList";
import { buildPlaygroundKnowledgeReferencesFromSources } from "../../ai-shared/retrieval";
import type { PlaygroundSessionViewModel } from "../types";

type ThreadPanelProps = {
  activeSession: PlaygroundSessionViewModel | null;
  isBootstrapping: boolean;
  loadingText: string;
  emptyStateText: string;
  threadRef: RefObject<HTMLDivElement>;
  handleScroll: () => void;
  hasUnreadContentBelow: boolean;
  isPinnedToBottom: boolean;
  scrollToBottom: (options?: { behavior?: ScrollBehavior; force?: boolean }) => void;
  composer: ReactNode;
  composerHeight: number;
};

export default function ThreadPanel({
  activeSession,
  isBootstrapping,
  loadingText,
  emptyStateText,
  threadRef,
  handleScroll,
  hasUnreadContentBelow,
  isPinnedToBottom,
  scrollToBottom,
  composer,
  composerHeight,
}: ThreadPanelProps): JSX.Element {
  const { t } = useTranslation("common");
  const { showErrorFeedback } = useActionFeedback();
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const copiedResetTimeoutRef = useRef<number | null>(null);
  const shellStyle = {
    ["--chatbot-composer-height" as string]: `${composerHeight}px`,
  } as CSSProperties;
  const copyLabel = t("playgrounds.messageActions.copy");
  const copiedLabel = t("playgrounds.messageActions.copied");
  const copyFailedLabel = t("playgrounds.messageActions.copyFailed");

  useEffect(() => () => {
    if (copiedResetTimeoutRef.current !== null) {
      window.clearTimeout(copiedResetTimeoutRef.current);
    }
  }, []);

  const handleCopyMessage = async (messageId: string, content: string): Promise<void> => {
    if (!navigator.clipboard?.writeText) {
      showErrorFeedback(copyFailedLabel, copyFailedLabel);
      return;
    }

    try {
      await navigator.clipboard.writeText(content);
      setCopiedMessageId(messageId);
      if (copiedResetTimeoutRef.current !== null) {
        window.clearTimeout(copiedResetTimeoutRef.current);
      }
      copiedResetTimeoutRef.current = window.setTimeout(() => {
        setCopiedMessageId((current) => (current === messageId ? null : current));
        copiedResetTimeoutRef.current = null;
      }, 2000);
    } catch (error) {
      showErrorFeedback(error, copyFailedLabel);
    }
  };

  return (
    <div
      ref={threadRef}
      className="chatbot-thread-shell"
      onScroll={handleScroll}
      style={shellStyle}
    >
      <div
        className="chatbot-thread"
        aria-live="polite"
      >
        {activeSession?.messages.length
          ? activeSession.messages.map((message) => {
            const storedReferences = getPlaygroundMessageReferences(message.metadata);
            const references = storedReferences.length > 0
              ? storedReferences
              : buildPlaygroundKnowledgeReferencesFromSources(getPlaygroundMessageSources(message.metadata));
            return (
              <article
                key={message.id}
                className={`chatbot-message chatbot-message-${message.role}`}
              >
                <div className="chatbot-message-surface">
                  <ChatMessageBody
                    content={message.content}
                    renderMarkdown={message.role === "assistant"}
                  />
                  {message.role === "assistant" && references.length > 0 ? (
                    <KnowledgeReferencesList references={references} messageId={message.id} />
                  ) : null}
                  {message.role === "assistant" ? (
                    <div
                      className="chatbot-message-actions"
                      data-copied={copiedMessageId === message.id ? "true" : "false"}
                    >
                      <button
                        type="button"
                        className="chatbot-message-copy-button"
                        aria-label={copiedMessageId === message.id ? copiedLabel : copyLabel}
                        title={copiedMessageId === message.id ? copiedLabel : copyLabel}
                        onClick={() => void handleCopyMessage(message.id, message.content)}
                      >
                        <span className="chatbot-message-copy-icon" aria-hidden="true">
                          <svg viewBox="0 0 24 24" focusable="false">
                            <rect x="9.25" y="8.25" width="9.5" height="11.25" rx="2" />
                            <path d="M14.75 6.75v-1A2.25 2.25 0 0 0 12.5 3.5h-6a2.25 2.25 0 0 0-2.25 2.25v8.5A2.25 2.25 0 0 0 6.5 16.5h1" />
                          </svg>
                        </span>
                        <span className="sr-only">{copiedMessageId === message.id ? copiedLabel : copyLabel}</span>
                      </button>
                      <span
                        className="chatbot-message-copy-status"
                        aria-live="polite"
                      >
                        {copiedMessageId === message.id ? copiedLabel : ""}
                      </span>
                    </div>
                  ) : null}
                </div>
              </article>
            );
          })
          : <p className="status-text chatbot-thread-status">
            {isBootstrapping ? loadingText : emptyStateText}
          </p>}
      </div>
      <div className="chatbot-thread-composer-slot">
        {composer}
      </div>
      {hasUnreadContentBelow && !isPinnedToBottom
        ? (
          <button
            type="button"
            className="btn btn-secondary chatbot-jump-to-latest"
            onClick={() => scrollToBottom({ behavior: "smooth" })}
          >
            Jump to latest
          </button>
        )
        : null}
    </div>
  );
}
