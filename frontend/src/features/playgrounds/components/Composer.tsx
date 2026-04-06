import { useAutoResizingComposer } from "../hooks/useAutoResizingComposer";

type ComposerProps = {
  draft: string;
  error: string;
  disabled: boolean;
  submitLabel: string;
  busyLabel: string;
  stopLabel: string;
  isSending: boolean;
  canStop: boolean;
  placeholder: string;
  onDraftChange: (value: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
  onHeightChange?: (height: number) => void;
};

export default function Composer({
  draft,
  error,
  disabled,
  submitLabel,
  busyLabel,
  stopLabel,
  isSending,
  canStop,
  placeholder,
  onDraftChange,
  onSubmit,
  onCancel,
  onHeightChange,
}: ComposerProps): JSX.Element {
  const {
    shellRef,
    textareaRef,
    handleKeyDown,
    handleActionClick,
    isActionDisabled,
    isTextareaDisabled,
  } = useAutoResizingComposer({
    draft,
    disabled,
    isSending,
    canStop,
    onSubmit,
    onCancel,
    onHeightChange,
  });

  const actionLabel = isSending
    ? (canStop ? stopLabel : busyLabel)
    : submitLabel;

  return (
    <div ref={shellRef} className="chatbot-composer-shell">
      <label className="sr-only" htmlFor="prompt">Message</label>
      <textarea
        ref={textareaRef}
        id="prompt"
        aria-label="Message"
        className="field-input chatbot-composer-input"
        value={draft}
        onChange={(event) => onDraftChange(event.currentTarget.value)}
        onKeyDown={handleKeyDown}
        rows={1}
        placeholder={placeholder}
        disabled={isTextareaDisabled}
      />

      <button
        type="button"
        className={`chatbot-composer-action ${canStop ? "chatbot-composer-action-stop" : "chatbot-composer-action-send"}`}
        onClick={handleActionClick}
        disabled={isActionDisabled}
        aria-label={actionLabel}
        title={actionLabel}
      >
        <span className="sr-only">{actionLabel}</span>
        <span className="chatbot-composer-action-icon" aria-hidden="true">
          {canStop
            ? (
              <svg viewBox="0 0 24 24" focusable="false">
                <path d="M7 7h10v10H7z" />
              </svg>
            )
            : (
              <svg viewBox="0 0 24 24" focusable="false">
                <path d="M3.6 19.4 21 12 3.6 4.6l.1 5.8 10.4 1.6-10.4 1.6-.1 5.8Z" />
              </svg>
            )}
        </span>
      </button>

      {error ? <p className="status-text error-text">{error}</p> : null}
    </div>
  );
}
