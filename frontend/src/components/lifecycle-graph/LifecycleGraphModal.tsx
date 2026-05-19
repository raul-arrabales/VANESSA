import { useRef } from "react";
import ModalDialog from "../ModalDialog";
import LifecycleGraph from "./LifecycleGraph";
import type { LifecycleGraphModalProps } from "./types";

export function LifecycleGraphModal({
  title,
  description,
  closeLabel,
  onClose,
  ...graphProps
}: LifecycleGraphModalProps): JSX.Element {
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  return (
    <ModalDialog
      className="lifecycle-graph-modal"
      title={title}
      description={description}
      onClose={onClose}
      initialFocusRef={closeButtonRef}
      actions={(
        <button ref={closeButtonRef} type="button" className="btn btn-primary" onClick={onClose}>
          {closeLabel}
        </button>
      )}
    >
      <LifecycleGraph {...graphProps} />
    </ModalDialog>
  );
}
