import { useRef, useState } from "react";
import type { PlaygroundImageContentPart } from "../../../api/playgrounds";
import { useAutoResizingComposer } from "../hooks/useAutoResizingComposer";
import ComposerAttachmentsTray from "./ComposerAttachmentsTray";

type ComposerProps = {
  draft: string;
  error: string;
  disabled: boolean;
  submitLabel: string;
  busyLabel: string;
  stopLabel: string;
  isSending: boolean;
  isUploadingAttachment?: boolean;
  canStop: boolean;
  placeholder: string;
  pendingImages?: PlaygroundImageContentPart[];
  onDraftChange: (value: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
  onAddImages?: (files: FileList) => void;
  onRemoveImage?: (imageRef: string) => void;
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
  isUploadingAttachment = false,
  canStop,
  placeholder,
  pendingImages = [],
  onDraftChange,
  onSubmit,
  onCancel,
  onAddImages,
  onRemoveImage,
  onHeightChange,
}: ComposerProps): JSX.Element {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [isAddMenuOpen, setIsAddMenuOpen] = useState(false);
  const canSubmit = Boolean(draft.trim()) || pendingImages.length > 0;
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
    canSubmit,
  });

  const actionLabel = isSending
    ? (canStop ? stopLabel : busyLabel)
    : submitLabel;

  return (
    <div ref={shellRef} className="chatbot-composer-shell">
      <ComposerAttachmentsTray
        pendingImages={pendingImages}
        isSending={isSending}
        onRemoveImage={onRemoveImage}
      />
      <label className="sr-only" htmlFor="prompt">Message</label>
      <div className="chatbot-composer-input-wrap">
        <button
          type="button"
          className="chatbot-composer-add"
          aria-label="Add content"
          aria-expanded={isAddMenuOpen}
          onClick={() => setIsAddMenuOpen((current) => !current)}
          disabled={disabled || isSending || isUploadingAttachment}
        >
          <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
            <path d="M12 5v14M5 12h14" />
          </svg>
        </button>
        {isAddMenuOpen ? (
          <div className="chatbot-composer-add-menu" role="menu">
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setIsAddMenuOpen(false);
                fileInputRef.current?.click();
              }}
            >
              Image
            </button>
          </div>
        ) : null}
        <input
          ref={fileInputRef}
          className="sr-only"
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif"
          multiple
          onChange={(event) => {
            if (event.currentTarget.files?.length) {
              onAddImages?.(event.currentTarget.files);
            }
            event.currentTarget.value = "";
          }}
        />
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
      </div>

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
      {isUploadingAttachment ? <p className="status-text">Uploading image...</p> : null}
    </div>
  );
}
