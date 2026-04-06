import type { CSSProperties, ReactNode, RefObject } from "react";
import ChatMessageBody from "../../../components/ChatMessageBody";
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
  const shellStyle = {
    ["--chatbot-composer-height" as string]: `${composerHeight}px`,
  } as CSSProperties;

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
            const sources = Array.isArray(message.metadata.sources)
              ? message.metadata.sources as Array<Record<string, unknown>>
              : [];
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
                  {message.role === "assistant" && sources.length > 0 ? (
                    <div className="card-stack">
                      {sources.map((source, index) => (
                        <div key={String(source.id ?? source.title ?? index)} className="panel">
                          <strong>{String(source.title ?? source.id ?? "Source")}</strong>
                          <p>{String(source.snippet ?? "")}</p>
                        </div>
                      ))}
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
