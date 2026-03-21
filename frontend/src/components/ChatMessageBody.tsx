import { Suspense, lazy } from "react";

type ChatMessageBodyProps = {
  content: string;
  renderMarkdown: boolean;
};

const MarkdownMessageBody = lazy(() => import("./MarkdownMessageBody"));

export default function ChatMessageBody({
  content,
  renderMarkdown,
}: ChatMessageBodyProps): JSX.Element {
  if (!renderMarkdown) {
    return <p className="chatbot-message-text">{content}</p>;
  }

  return (
    <Suspense fallback={<p className="chatbot-message-text">Loading message...</p>}>
      <MarkdownMessageBody content={content} />
    </Suspense>
  );
}
