import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { activateDeploymentProfile, type PlatformDeploymentProfile } from "../../../api/platform";
import { useActionFeedback } from "../../../feedback/ActionFeedbackProvider";
import { formatActivationValidationError } from "../validationFeedback";
import PlatformDeploymentActivationDialog from "./PlatformDeploymentActivationDialog";

type PlatformDeploymentQuickSwitchProps = {
  activeDeployment: PlatformDeploymentProfile | null;
  deployments: PlatformDeploymentProfile[];
  isRefreshing: boolean;
  token: string;
  onActivated: () => Promise<void>;
};

export default function PlatformDeploymentQuickSwitch({
  activeDeployment,
  deployments,
  isRefreshing,
  token,
  onActivated,
}: PlatformDeploymentQuickSwitchProps): JSX.Element {
  const { t } = useTranslation("common");
  const { showErrorFeedback, showSuccessFeedback } = useActionFeedback();
  const [selectedDeploymentId, setSelectedDeploymentId] = useState("");
  const [confirmDeployment, setConfirmDeployment] = useState<PlatformDeploymentProfile | null>(null);
  const [isActivating, setIsActivating] = useState(false);

  const readyDeployments = useMemo(
    () =>
      deployments.filter((deployment) =>
        deployment.configuration_status?.is_ready === true
        && !deployment.is_active
        && deployment.id !== activeDeployment?.id,
      ),
    [activeDeployment?.id, deployments],
  );

  useEffect(() => {
    if (readyDeployments.length === 0) {
      setSelectedDeploymentId("");
      return;
    }
    if (!readyDeployments.some((deployment) => deployment.id === selectedDeploymentId)) {
      setSelectedDeploymentId(readyDeployments[0].id);
    }
  }, [readyDeployments, selectedDeploymentId]);

  const selectedDeployment = readyDeployments.find((deployment) => deployment.id === selectedDeploymentId) ?? null;
  const hasReadyDeployments = readyDeployments.length > 0;

  async function handleConfirmActivation(): Promise<void> {
    if (!token || !confirmDeployment) {
      return;
    }

    const targetDeployment = confirmDeployment;
    setConfirmDeployment(null);
    setIsActivating(true);
    try {
      await activateDeploymentProfile(targetDeployment.id, token);
      showSuccessFeedback(t("platformControl.feedback.activationSuccess", { name: targetDeployment.display_name }));
      await onActivated();
    } catch (error) {
      showErrorFeedback(formatActivationValidationError(error) ?? error, t("platformControl.feedback.activationFailed"));
    } finally {
      setIsActivating(false);
    }
  }

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h3 className="section-title">{t("platformControl.quickSwitch.title")}</h3>
        <p className="status-text">{t("platformControl.quickSwitch.description")}</p>
      </div>

      {hasReadyDeployments ? (
        <div className="platform-quick-switch">
          <label className="control-group" htmlFor="platform-quick-switch-deployment">
            <span className="field-label">{t("platformControl.quickSwitch.deploymentLabel")}</span>
            <select
              id="platform-quick-switch-deployment"
              className="field-input"
              value={selectedDeploymentId}
              onChange={(event) => setSelectedDeploymentId(event.currentTarget.value)}
              disabled={isRefreshing || isActivating}
            >
              {readyDeployments.map((deployment) => (
                <option key={deployment.id} value={deployment.id}>
                  {deployment.display_name}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!selectedDeployment || isRefreshing || isActivating}
            onClick={() => {
              if (selectedDeployment) {
                setConfirmDeployment(selectedDeployment);
              }
            }}
          >
            {isActivating ? t("platformControl.actions.activating") : t("platformControl.quickSwitch.activateSelected")}
          </button>
        </div>
      ) : (
        <p className="status-text">{t("platformControl.quickSwitch.empty")}</p>
      )}

      {confirmDeployment ? (
        <PlatformDeploymentActivationDialog
          activeDeployment={activeDeployment}
          deployment={confirmDeployment}
          isPending={isActivating}
          onCancel={() => setConfirmDeployment(null)}
          onConfirm={() => {
            void handleConfirmActivation();
          }}
        />
      ) : null}
    </article>
  );
}
