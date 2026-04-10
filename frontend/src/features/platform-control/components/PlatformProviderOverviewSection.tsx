import { useTranslation } from "react-i18next";
import type { PlatformDeploymentProfile, PlatformProvider, PlatformProviderFamily } from "../../../api/platform";

type PlatformProviderOverviewSectionProps = {
  activeDeployment: PlatformDeploymentProfile | null;
  isUsedByActiveDeployment: boolean;
  provider: PlatformProvider;
  providerFamily: PlatformProviderFamily | null;
};

export default function PlatformProviderOverviewSection({
  activeDeployment,
  isUsedByActiveDeployment,
  provider,
  providerFamily,
}: PlatformProviderOverviewSectionProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <article className="panel card-stack">
      <div className="platform-card-header">
        <div className="status-row">
          <h3 className="section-title">{provider.display_name}</h3>
          <span className="status-text">
            <code className="code-inline">{provider.slug}</code>
          </span>
        </div>
        <div className="inline-meta-list">
          <span className="platform-badge" data-tone={provider.enabled ? "enabled" : "disabled"}>
            {provider.enabled ? t("platformControl.badges.enabled") : t("platformControl.badges.disabled")}
          </span>
          {isUsedByActiveDeployment ? (
            <span className="platform-badge" data-tone="active">
              {t("platformControl.badges.activeDeployment")}
            </span>
          ) : null}
        </div>
      </div>
      <p className="status-text">{provider.description || t("platformControl.providers.noDescription")}</p>
      <div className="platform-detail-grid">
        <div className="summary-card">
          <span className="field-label">{t("platformControl.providers.familyLabel")}</span>
          <strong>{providerFamily?.display_name ?? provider.provider_key}</strong>
          <span className="status-text">{provider.provider_key}</span>
        </div>
        <div className="summary-card">
          <span className="field-label">{t("platformControl.providers.capabilityLabel")}</span>
          <strong>{provider.capability}</strong>
          <span className="status-text">{provider.adapter_kind}</span>
        </div>
        <div className="summary-card">
          <span className="field-label">{t("platformControl.providers.endpointLabel")}</span>
          <strong>{provider.endpoint_url}</strong>
          <span className="status-text">{provider.healthcheck_url ?? t("platformControl.summary.none")}</span>
        </div>
        <div className="summary-card">
          <span className="field-label">{t("platformControl.providers.activeDeploymentLabel")}</span>
          <strong>{activeDeployment?.display_name ?? t("platformControl.summary.none")}</strong>
          <span className="status-text">
            {isUsedByActiveDeployment
              ? t("platformControl.providers.activeReference")
              : t("platformControl.providers.inactiveReference")}
          </span>
        </div>
      </div>
    </article>
  );
}
