import type { RefObject } from "react";
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
}: ThreadPanelProps): JSX.Element {
  return (
    <div className="chatbot-thread-shell">
      <div
        ref={threadRef}
        className="chatbot-thread"
        aria-live="polite"
        onScroll={handleScroll}
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
                <p className="chatbot-message-role">{message.role === "user" ? "You" : "Assistant"}</p>
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
              </article>
            );
          })
          : <p className="status-text">
            {isBootstrapping ? loadingText : emptyStateText}
          </p>}
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
