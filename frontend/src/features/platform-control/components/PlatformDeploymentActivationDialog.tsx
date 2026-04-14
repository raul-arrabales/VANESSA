import { useRef } from "react";
import { useTranslation } from "react-i18next";
import ModalDialog from "../../../components/ModalDialog";
import type { PlatformDeploymentProfile } from "../../../api/platform";

type PlatformDeploymentActivationDialogProps = {
  activeDeployment: PlatformDeploymentProfile | null;
  deployment: PlatformDeploymentProfile;
  isPending: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

export default function PlatformDeploymentActivationDialog({
  activeDeployment,
  deployment,
  isPending,
  onCancel,
  onConfirm,
}: PlatformDeploymentActivationDialogProps): JSX.Element {
  const { t } = useTranslation("common");
  const confirmButtonRef = useRef<HTMLButtonElement | null>(null);
  const description = activeDeployment
    ? t("platformControl.deployments.activationDialogDescription", {
        current: activeDeployment.display_name,
        target: deployment.display_name,
      })
    : t("platformControl.deployments.activationDialogDescriptionNoCurrent", {
        target: deployment.display_name,
      });

  return (
    <ModalDialog
      eyebrow={t("platformControl.deployments.activationDialogEyebrow")}
      title={t("platformControl.deployments.activationDialogTitle")}
      description={description}
      onClose={onCancel}
      closeDisabled={isPending}
      initialFocusRef={confirmButtonRef}
      actions={(
        <>
          <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={isPending}>
            {t("platformControl.actions.cancel")}
          </button>
          <button
            ref={confirmButtonRef}
            type="button"
            className="btn btn-primary"
            onClick={onConfirm}
            disabled={isPending}
          >
            {isPending ? t("platformControl.actions.activating") : t("platformControl.actions.confirmActivate")}
          </button>
        </>
      )}
    >
      <div className="card-stack">
        <p className="status-text">
          <strong>{t("platformControl.deployments.activationDialogCurrent")}</strong>{" "}
          {activeDeployment?.display_name ?? t("platformControl.summary.none")}
        </p>
        <p className="status-text">
          <strong>{t("platformControl.deployments.activationDialogTarget")}</strong>{" "}
          {deployment.display_name}
        </p>
      </div>
    </ModalDialog>
  );
}
