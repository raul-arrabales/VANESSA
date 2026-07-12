import { useRef } from "react";
import { useTranslation } from "react-i18next";
import ModalDialog from "../../../components/ModalDialog";

type Props = {
  capabilityName: string;
  isPending: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

export default function PlatformDeploymentBindingRemovalDialog({
  capabilityName,
  isPending,
  onCancel,
  onConfirm,
}: Props): JSX.Element {
  const { t } = useTranslation("common");
  const confirmButtonRef = useRef<HTMLButtonElement | null>(null);
  return (
    <ModalDialog
      eyebrow={t("platformControl.deployments.bindingRemovalDialogEyebrow")}
      title={t("platformControl.deployments.bindingRemovalDialogTitle", { capability: capabilityName })}
      description={t("platformControl.deployments.bindingRemovalDialogDescription")}
      onClose={onCancel}
      closeDisabled={isPending}
      initialFocusRef={confirmButtonRef}
      actions={<>
        <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={isPending}>
          {t("platformControl.actions.cancel")}
        </button>
        <button ref={confirmButtonRef} type="button" className="btn btn-danger" onClick={onConfirm} disabled={isPending}>
          {isPending ? t("platformControl.actions.removing") : t("platformControl.actions.confirmRemoveBinding")}
        </button>
      </>}
    />
  );
}
