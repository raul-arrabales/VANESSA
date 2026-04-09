import { useEffect, useId, type ReactNode, type RefObject } from "react";

type ModalDialogProps = {
  title: string;
  description?: string;
  eyebrow?: string;
  onClose: () => void;
  closeDisabled?: boolean;
  initialFocusRef?: RefObject<HTMLElement>;
  className?: string;
  children?: ReactNode;
  actions?: ReactNode;
};

export default function ModalDialog({
  title,
  description,
  eyebrow,
  onClose,
  closeDisabled = false,
  initialFocusRef,
  className,
  children,
  actions,
}: ModalDialogProps): JSX.Element {
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    initialFocusRef?.current?.focus();
  }, [initialFocusRef]);

  useEffect(() => {
    const handleEscapePress = (event: KeyboardEvent): void => {
      if (event.key === "Escape" && !closeDisabled) {
        onClose();
      }
    };

    document.addEventListener("keydown", handleEscapePress);
    return () => {
      document.removeEventListener("keydown", handleEscapePress);
    };
  }, [closeDisabled, onClose]);

  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onClick={() => {
        if (!closeDisabled) {
          onClose();
        }
      }}
    >
      <div
        className={className ? `modal-card panel ${className}` : "modal-card panel"}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
        onClick={(event) => event.stopPropagation()}
      >
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <h2 id={titleId} className="section-title modal-title">{title}</h2>
        {description ? <p id={descriptionId} className="modal-message">{description}</p> : null}
        {children}
        {actions ? <div className="modal-actions">{actions}</div> : null}
      </div>
    </div>
  );
}
