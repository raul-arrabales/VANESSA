type ComposerProps = {
  draft: string;
  error: string;
  disabled: boolean;
  submitLabel: string;
  busyLabel: string;
  isSending: boolean;
  placeholder: string;
  onDraftChange: (value: string) => void;
  onSubmit: () => void;
};

export default function Composer({
  draft,
  error,
  disabled,
  submitLabel,
  busyLabel,
  isSending,
  placeholder,
  onDraftChange,
  onSubmit,
}: ComposerProps): JSX.Element {
  return (
    <>
      <label className="field-label" htmlFor="prompt">Message</label>
      <textarea
        id="prompt"
        aria-label="Message"
        className="field-input"
        value={draft}
        onChange={(event) => onDraftChange(event.currentTarget.value)}
        rows={4}
        placeholder={placeholder}
        disabled={disabled}
      />

      <button
        type="button"
        className="btn btn-primary"
        onClick={onSubmit}
        disabled={disabled || !draft.trim()}
      >
        {isSending ? busyLabel : submitLabel}
      </button>

      {error ? <p className="status-text error-text">{error}</p> : null}
    </>
  );
}
