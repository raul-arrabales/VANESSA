import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { PlatformDeploymentProfile, PlatformProvider, PlatformProviderFamily } from "../../../api/platform";
import { getActiveDeployment, getProviderUsageEntries } from "../platformTopology";

type PlatformProvidersDirectoryProps = {
  providers: PlatformProvider[];
  providerFamilies: PlatformProviderFamily[];
  deployments: PlatformDeploymentProfile[];
};

function providerOrigin(providerKey: string): "cloud" | "local" {
  const normalizedProviderKey = providerKey.trim().toLowerCase();
  return normalizedProviderKey.includes("_cloud") || normalizedProviderKey.endsWith("_cloud") ? "cloud" : "local";
}

export default function PlatformProvidersDirectory({
  providers,
  providerFamilies,
  deployments,
}: PlatformProvidersDirectoryProps): JSX.Element {
  const { t } = useTranslation("common");
  const providerFamilyByKey = new Map(providerFamilies.map((family) => [family.provider_key, family]));
  const activeDeployment = getActiveDeployment(deployments);

  if (providers.length === 0) {
    return <p className="status-text">{t("platformControl.providers.empty")}</p>;
  }

  return (
    <div className="platform-directory-grid platform-provider-list">
      {providers.map((provider) => {
        const family = providerFamilyByKey.get(provider.provider_key);
        const usageEntries = getProviderUsageEntries(provider.id, deployments);
        const usesActiveDeployment = usageEntries.some((entry) => entry.deployment.is_active);
        const origin = providerOrigin(provider.provider_key);
        return (
          <article key={provider.id} className="platform-deployment-card platform-provider-row">
            <div className="platform-provider-summary">
              <div className="status-row">
                <h3 className="section-title">{provider.display_name}</h3>
                <code className="code-inline platform-provider-code" title={provider.slug}>
                  {provider.slug}
                </code>
              </div>
              <div className="inline-meta-list">
                <span className="platform-badge" data-tone={provider.enabled ? "enabled" : "disabled"}>
                  {provider.enabled ? t("platformControl.badges.enabled") : t("platformControl.badges.disabled")}
                </span>
                <span className="platform-badge" data-tone={origin}>
                  {t(`platformControl.badges.${origin}`)}
                </span>
                {usesActiveDeployment ? (
                  <span className="platform-badge" data-tone="active">
                    {t("platformControl.badges.activeDeployment")}
                  </span>
                ) : null}
              </div>
              <p className="status-text platform-provider-description">
                {provider.description || t("platformControl.providers.noDescription")}
              </p>
            </div>
            <div className="platform-provider-details">
              <div className="platform-provider-detail">
                <span className="field-label">{t("platformControl.providers.familyLabel")}</span>
                <span className="platform-provider-value">{family?.display_name ?? provider.provider_key}</span>
              </div>
              <div className="platform-provider-detail">
                <span className="field-label">{t("platformControl.providers.capabilityLabel")}</span>
                <span className="platform-provider-value">{provider.capability}</span>
              </div>
              <div className="platform-provider-detail">
                <span className="field-label">{t("platformControl.providers.endpointLabel")}</span>
                <code className="code-inline platform-provider-code" title={provider.endpoint_url}>
                  {provider.endpoint_url}
                </code>
              </div>
              <div className="platform-provider-detail">
                <span className="field-label">{t("platformControl.providers.usedByDeployments")}</span>
                <div className="platform-provider-value">
                  <span>{usageEntries.length}</span>
                  {usageEntries.length > 0 ? (
                    <div className="inline-meta-list platform-provider-usage-list">
                      {usageEntries.slice(0, 2).map((entry) => (
                        <span key={entry.deployment.id} className="status-text">
                          {entry.deployment.display_name}
                          {activeDeployment?.id === entry.deployment.id ? ` (${t("platformControl.providers.activeReference")})` : ""}
                        </span>
                      ))}
                      {usageEntries.length > 2 ? (
                        <span className="status-text">
                          {t("platformControl.providers.moreDeployments", { count: usageEntries.length - 2 })}
                        </span>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
            <div className="inline-meta-list platform-provider-actions">
              <Link className="btn btn-secondary" to={`/control/platform/providers/${provider.id}`}>
                {t("platformControl.actions.openProvider")}
              </Link>
            </div>
          </article>
        );
      })}
    </div>
  );
}
