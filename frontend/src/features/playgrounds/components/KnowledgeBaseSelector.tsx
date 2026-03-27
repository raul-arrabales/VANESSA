import type { PlaygroundKnowledgeBaseOption } from "../../../api/playgrounds";

type KnowledgeBaseSelectorProps = {
  knowledgeBases: PlaygroundKnowledgeBaseOption[];
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
};

export default function KnowledgeBaseSelector({
  knowledgeBases,
  value,
  disabled,
  onChange,
}: KnowledgeBaseSelectorProps): JSX.Element {
  return (
    <label>
      Knowledge base
      <select
        aria-label="Knowledge base"
        value={value}
        onChange={(event) => onChange(event.currentTarget.value)}
        disabled={disabled}
      >
        {knowledgeBases.map((knowledgeBase) => (
          <option key={knowledgeBase.id} value={knowledgeBase.id}>{knowledgeBase.display_name}</option>
        ))}
      </select>
    </label>
  );
}
