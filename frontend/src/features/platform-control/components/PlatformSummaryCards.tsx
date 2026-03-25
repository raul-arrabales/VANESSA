import { useTranslation } from "react-i18next";
import type { PlatformActivationAuditEntry, PlatformDeploymentProfile } from "../../../api/platform";
import type { LoadState } from "../platformControlState";

type PlatformSummaryCardsProps = {
  state: LoadState;
  activeDeployment: PlatformDeploymentProfile | null;
  latestActivation: PlatformActivationAuditEntry | null;
  coveredRequiredCapabilities: number;
  requiredCapabilities: number;
};

export default function PlatformSummaryCards({
  state,
  activeDeployment,
  latestActivation,
  coveredRequiredCapabilities,
  requiredCapabilities,
}: PlatformSummaryCardsProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <div className="platform-summary-grid">
      <div className="platform-summary-card">
        <span className="field-label">{t("platformControl.summary.activeDeployment")}</span>
        <strong>{activeDeployment?.display_name ?? t("platformControl.summary.none")}</strong>
        <span className="status-text">{activeDeployment?.slug ?? t("platformControl.summary.none")}</span>
      </div>
      <div className="platform-summary-card">
        <span className="field-label">{t("platformControl.summary.requiredCoverage")}</span>
        <strong>{`${coveredRequiredCapabilities}/${requiredCapabilities}`}</strong>
        <span className="status-text">{t("platformControl.summary.requiredCoverageDescription")}</span>
      </div>
      <div className="platform-summary-card">
        <span className="field-label">{t("platformControl.summary.lastActivation")}</span>
        <strong>{latestActivation?.deployment_profile.display_name ?? t("platformControl.summary.none")}</strong>
        <span className="status-text">{latestActivation?.activated_at ?? t("platformControl.summary.none")}</span>
      </div>
      <div className="platform-summary-card">
        <span className="field-label">{t("platformControl.summary.loadState")}</span>
        <span className="platform-badge" data-tone={state === "success" ? "active" : state === "error" ? "inactive" : "required"}>
          {t(`platformControl.state.${state}`)}
        </span>
      </div>
    </div>
  );
}
