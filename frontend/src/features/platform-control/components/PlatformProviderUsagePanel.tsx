import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { PlatformCapability, PlatformDeploymentProfile } from "../../../api/platform";
import { getProviderUsageEntries, summarizeBindingResources } from "../platformTopology";

type PlatformProviderUsagePanelProps = {
  providerId: string;
  capabilities: PlatformCapability[];
  deployments: PlatformDeploymentProfile[];
};

export default function PlatformProviderUsagePanel({
  providerId,
  capabilities,
  deployments,
}: PlatformProviderUsagePanelProps): JSX.Element {
  const { t } = useTranslation("common");
  const capabilityLabelByKey = new Map(capabilities.map((capability) => [capability.capability, capability.display_name]));
  const usageEntries = getProviderUsageEntries(providerId, deployments);

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h3 className="section-title">{t("platformControl.sections.usage")}</h3>
        <p className="status-text">{t("platformControl.providers.usageDescription")}</p>
      </div>

      {usageEntries.length === 0 ? (
        <p className="status-text">{t("platformControl.providers.noUsage")}</p>
      ) : (
        <div className="platform-deployment-list">
          {usageEntries.map((entry) => (
            <article key={entry.deployment.id} className="platform-deployment-card">
              <div className="platform-card-header">
                <div className="status-row">
                  <h4 className="section-title">{entry.deployment.display_name}</h4>
                  <span className="status-text">
                    <code className="code-inline">{entry.deployment.slug}</code>
                  </span>
                </div>
                <span className="platform-badge" data-tone={entry.deployment.is_active ? "active" : "inactive"}>
                  {entry.deployment.is_active ? t("platformControl.badges.activeDeployment") : t("platformControl.badges.inactive")}
                </span>
              </div>
              <div className="health-table-wrap">
                <table className="health-table" aria-label={t("platformControl.providers.usageTableAria", { name: entry.deployment.display_name })}>
                  <thead>
                    <tr>
                      <th>{t("platformControl.deployments.columns.capability")}</th>
                      <th>{t("platformControl.deployments.columns.resources")}</th>
                      <th>{t("platformControl.deployments.columns.adapter")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {entry.bindings.map((binding) => (
                      <tr key={`${entry.deployment.id}-${binding.capability}`}>
                        <td>{capabilityLabelByKey.get(binding.capability) ?? binding.capability}</td>
                        <td>{summarizeBindingResources(binding, t("platformControl.summary.none"))}</td>
                        <td>{binding.provider.adapter_kind}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="platform-inline-meta">
                <Link className="btn btn-secondary" to={`/control/platform/deployments/${entry.deployment.id}`}>
                  {t("platformControl.actions.openDeployment")}
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </article>
  );
}
