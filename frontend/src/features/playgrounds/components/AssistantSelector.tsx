import type { PlaygroundAssistantOption } from "../../../api/playgrounds";

type AssistantSelectorProps = {
  assistants: PlaygroundAssistantOption[];
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
};

export default function AssistantSelector({
  assistants,
  value,
  disabled,
  onChange,
}: AssistantSelectorProps): JSX.Element {
  return (
    <label>
      Assistant
      <select
        aria-label="Assistant"
        value={value}
        onChange={(event) => onChange(event.currentTarget.value)}
        disabled={disabled}
      >
        {assistants.map((assistant) => (
          <option key={assistant.assistant_ref} value={assistant.assistant_ref}>{assistant.display_name}</option>
        ))}
      </select>
    </label>
  );
}
