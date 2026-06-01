import { useEffect, useRef, useState, type CSSProperties, type ReactNode, type RefObject } from "react";
import { useTranslation } from "react-i18next";
import ChatMessageBody from "../../../components/ChatMessageBody";
import { useAuth } from "../../../auth/AuthProvider";
import { useActionFeedback } from "../../../feedback/ActionFeedbackProvider";
import { getPlaygroundMessageReferences, getPlaygroundMessageSources } from "../../../api/playgrounds";
import KnowledgeReferencesList from "../../ai-shared/KnowledgeReferencesList";
import { buildPlaygroundKnowledgeReferencesFromSources } from "../../ai-shared/retrieval";
import AssistantStatusTimeline from "./AssistantStatusTimeline";
import AttachmentImage, { downloadAttachmentImage } from "./AttachmentImage";
import { messageImageParts, messageText } from "../messageContent";
import type { PlaygroundImageContentPart } from "../../../api/playgrounds";
import type { PlaygroundRunStatus, PlaygroundSessionViewModel } from "../types";

type ThreadPanelProps = {
  activeSession: PlaygroundSessionViewModel | null;
  isBootstrapping: boolean;
  isSending: boolean;
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

function getMessageStatuses(metadata: Record<string, unknown>): PlaygroundRunStatus[] {
  return Array.isArray(metadata.statuses) ? metadata.statuses as PlaygroundRunStatus[] : [];
}

function TemporaryConversationIndicator(): JSX.Element {
  const label = "Temporary conversation - not saved";
  return (
    <div className="chatbot-temporary-indicator-wrap">
      <span
        className="chatbot-temporary-indicator"
        aria-label={label}
        title={label}
        role="img"
      >
        <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
          <path d="M6.5 5.5h11A2.5 2.5 0 0 1 20 8v6.5a2.5 2.5 0 0 1-2.5 2.5h-5.2L8 20v-3H6.5A2.5 2.5 0 0 1 4 14.5V8a2.5 2.5 0 0 1 2.5-2.5Z" />
          <path d="M8 10h8M8 13h5" />
        </svg>
      </span>
    </div>
  );
}

function ImageDownloadButton({ image }: { image: PlaygroundImageContentPart }): JSX.Element {
  const { token } = useAuth();
  const { showErrorFeedback } = useActionFeedback();
  return (
    <button
      type="button"
      className="chatbot-image-download"
      aria-label="Download image"
      title="Download image"
      onClick={() => {
        if (!token) {
          return;
        }
        void downloadAttachmentImage(image, token).catch((error) => {
          showErrorFeedback(error, "Image download failed");
        });
      }}
    >
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M12 4v10m0 0 4-4m-4 4-4-4M5 20h14" />
      </svg>
    </button>
  );
}

export default function ThreadPanel({
  activeSession,
  isBootstrapping,
  isSending,
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
  const [viewerImage, setViewerImage] = useState<PlaygroundImageContentPart | null>(null);
  const copiedResetTimeoutRef = useRef<number | null>(null);
  const shellStyle = {
    ["--chatbot-composer-height" as string]: `${composerHeight}px`,
  } as CSSProperties;
  const copyLabel = t("playgrounds.messageActions.copy");
  const copiedLabel = t("playgrounds.messageActions.copied");
  const copyFailedLabel = t("playgrounds.messageActions.copyFailed");
  const shouldShowStarterComposer = Boolean(activeSession)
    && activeSession?.messages.length === 0
    && !isBootstrapping
    && !isSending;
  const isTemporarySession = activeSession?.persistence === "temporary";

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

  if (shouldShowStarterComposer) {
    return (
      <div
        ref={threadRef}
        className="chatbot-thread-shell chatbot-thread-shell-starter"
        onScroll={handleScroll}
        style={shellStyle}
        data-temporary={isTemporarySession ? "true" : "false"}
      >
        {isTemporarySession ? <TemporaryConversationIndicator /> : null}
        <div className="chatbot-starter-composer">
          {composer}
        </div>
      </div>
    );
  }

  return (
    <div
      ref={threadRef}
      className="chatbot-thread-shell"
      onScroll={handleScroll}
      style={shellStyle}
      data-temporary={isTemporarySession ? "true" : "false"}
    >
      {isTemporarySession ? <TemporaryConversationIndicator /> : null}
      <div
        className="chatbot-thread"
        aria-live="polite"
      >
        {activeSession?.messages.length
          ? activeSession.messages.map((message) => {
            const text = messageText(message);
            const images = messageImageParts(message);
            const storedReferences = getPlaygroundMessageReferences(message.metadata);
            const references = storedReferences.length > 0
              ? storedReferences
              : buildPlaygroundKnowledgeReferencesFromSources(getPlaygroundMessageSources(message.metadata));
            const statuses = message.role === "assistant" ? getMessageStatuses(message.metadata) : [];
            const isLiveAssistantStatus = statuses.length > 0 && isSending && Boolean(message.metadata.transient);
            const statusTimeline = statuses.length > 0 ? (
              <AssistantStatusTimeline
                statuses={statuses}
                messageId={message.id}
                responseText={text}
                isLive={isLiveAssistantStatus}
              />
            ) : null;
            return (
              <article
                key={message.id}
                className={`chatbot-message chatbot-message-${message.role}`}
              >
                <div className="chatbot-message-surface">
                  {isLiveAssistantStatus ? statusTimeline : null}
                  {text.trim() ? (
                    <ChatMessageBody
                      content={text}
                      renderMarkdown={message.role === "assistant"}
                    />
                  ) : null}
                  {images.length > 0 ? (
                    <div className="chatbot-message-images" aria-label="Attached images">
                      {images.map((image) => (
                        <figure key={image.image_ref} className="chatbot-message-image">
                          <AttachmentImage
                            image={image}
                            className="chatbot-message-image-button"
                            onClick={() => setViewerImage(image)}
                          />
                          <ImageDownloadButton image={image} />
                        </figure>
                      ))}
                    </div>
                  ) : null}
                  {!isLiveAssistantStatus ? statusTimeline : null}
                  {message.role === "assistant" && references.length > 0 ? (
                    <KnowledgeReferencesList references={references} messageId={message.id} />
                  ) : null}
                  {message.role === "assistant" && text.trim() ? (
                    <div
                      className="chatbot-message-actions"
                      data-copied={copiedMessageId === message.id ? "true" : "false"}
                    >
                      <button
                        type="button"
                        className="chatbot-message-copy-button"
                        aria-label={copiedMessageId === message.id ? copiedLabel : copyLabel}
                        title={copiedMessageId === message.id ? copiedLabel : copyLabel}
                        onClick={() => void handleCopyMessage(message.id, text)}
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
      {viewerImage ? (
        <div className="chatbot-image-viewer" role="dialog" aria-modal="true" aria-label="Image preview">
          <div className="chatbot-image-viewer-backdrop" onClick={() => setViewerImage(null)} />
          <div className="chatbot-image-viewer-panel">
            <AttachmentImage image={viewerImage} className="chatbot-image-viewer-image" />
            <div className="chatbot-image-viewer-actions">
              <ImageDownloadButton image={viewerImage} />
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setViewerImage(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
