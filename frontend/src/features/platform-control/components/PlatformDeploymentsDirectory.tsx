import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { PlatformCapability, PlatformDeploymentProfile } from "../../../api/platform";
import { summarizeBindingResources } from "../platformTopology";

type PlatformDeploymentsDirectoryProps = {
  deployments: PlatformDeploymentProfile[];
  capabilities: PlatformCapability[];
};

export default function PlatformDeploymentsDirectory({
  deployments,
  capabilities,
}: PlatformDeploymentsDirectoryProps): JSX.Element {
  const { t } = useTranslation("common");
  const capabilityLabelByKey = new Map(capabilities.map((capability) => [capability.capability, capability.display_name]));

  if (deployments.length === 0) {
    return <p className="status-text">{t("platformControl.deployments.empty")}</p>;
  }

  return (
    <div className="platform-deployment-list">
      {deployments.map((deployment) => (
        <article key={deployment.id} className="platform-deployment-card">
          <div className="platform-card-header">
            <div className="status-row">
              <h3 className="section-title">{deployment.display_name}</h3>
              <span className="status-text">
                <code className="code-inline">{deployment.slug}</code>
              </span>
            </div>
            <span className="platform-badge" data-tone={deployment.is_active ? "active" : "inactive"}>
              {deployment.is_active ? t("platformControl.badges.active") : t("platformControl.badges.inactive")}
            </span>
          </div>
          {deployment.configuration_status ? (
            <div className="status-row">
              <span className="platform-badge" data-tone={deployment.configuration_status.is_ready ? "enabled" : "inactive"}>
                {deployment.configuration_status.is_ready
                  ? t("platformControl.badges.ready")
                  : t("platformControl.badges.incomplete")}
              </span>
              <p className="status-text">{deployment.configuration_status.summary}</p>
            </div>
          ) : null}
          <p className="status-text">{deployment.description || t("platformControl.deployments.noDescription")}</p>
          <div className="health-table-wrap">
            <table className="health-table" aria-label={t("platformControl.deployments.tableAria", { name: deployment.display_name })}>
              <thead>
                <tr>
                  <th>{t("platformControl.deployments.columns.capability")}</th>
                  <th>{t("platformControl.deployments.columns.provider")}</th>
                  <th>{t("platformControl.deployments.columns.resources")}</th>
                  <th>{t("platformControl.deployments.columns.adapter")}</th>
                  <th>{t("platformControl.deployments.columns.status")}</th>
                </tr>
              </thead>
              <tbody>
                {deployment.bindings.map((binding) => (
                  <tr key={`${deployment.id}-${binding.capability}`}>
                    <td>{capabilityLabelByKey.get(binding.capability) ?? binding.capability}</td>
                    <td>
                      <strong>{binding.provider.display_name}</strong>
                      <div className="inline-meta-list">
                        <code className="code-inline">{binding.provider.slug}</code>
                      </div>
                    </td>
                    <td>{summarizeBindingResources(binding, t("platformControl.summary.none"))}</td>
                    <td>{binding.provider.adapter_kind}</td>
                    <td>
                      <span
                        className="platform-badge"
                        data-tone={binding.configuration_status?.is_ready ? "enabled" : "inactive"}
                      >
                        {binding.configuration_status?.is_ready
                          ? t("platformControl.badges.ready")
                          : t("platformControl.badges.incomplete")}
                      </span>
                      {!binding.configuration_status?.is_ready ? (
                        <div className="inline-meta-list">
                          <span className="status-text">{binding.configuration_status?.summary ?? t("platformControl.summary.none")}</span>
                        </div>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="inline-meta-list">
            <Link className="btn btn-secondary" to={`/control/platform/deployments/${deployment.id}`}>
              {t("platformControl.actions.openDeployment")}
            </Link>
          </div>
        </article>
      ))}
    </div>
  );
}
