import type { PlaygroundKnowledgeSource } from "../../api/playgrounds";
import type { RetrievalDisplayItem } from "./retrieval";

type Props = {
  items: RetrievalDisplayItem<PlaygroundKnowledgeSource>[];
};

export default function KnowledgeSourcesList({ items }: Props): JSX.Element {
  if (items.length === 0) {
    return <></>;
  }

  return (
    <div className="knowledge-chat-source-list">
      {items.map((item) => (
        <div key={item.id} className="knowledge-chat-source">
          <strong className="knowledge-chat-source-title">{item.displayTitle}</strong>
          <p className="knowledge-chat-source-snippet">{item.displaySnippet}</p>
        </div>
      ))}
    </div>
  );
}
