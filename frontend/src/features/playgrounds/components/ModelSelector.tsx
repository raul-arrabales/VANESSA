type ModelSelectorProps = {
  models: Array<{ id: string; displayName: string }>;
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
};

export default function ModelSelector({
  models,
  value,
  disabled,
  onChange,
}: ModelSelectorProps): JSX.Element {
  return (
    <>
      <label className="field-label" htmlFor="model-picker">Model</label>
      <select
        id="model-picker"
        aria-label="Model"
        className="field-input"
        value={value}
        onChange={(event) => onChange(event.currentTarget.value)}
        disabled={disabled}
      >
        {models.length === 0 ? <option value="">No enabled models</option> : null}
        {models.map((model) => (
          <option key={model.id} value={model.id}>{model.displayName}</option>
        ))}
      </select>
    </>
  );
}
