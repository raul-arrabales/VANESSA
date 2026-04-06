import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { PlatformDeploymentProfile } from "../../../api/platform";
import { summarizeBindingResources } from "../platformTopology";

type PlatformDeploymentOverviewSectionProps = {
  activating: boolean;
  capabilityLabelByKey: Map<string, string>;
  deployment: PlatformDeploymentProfile;
  onActivate: () => void;
};

export default function PlatformDeploymentOverviewSection({
  activating,
  capabilityLabelByKey,
  deployment,
  onActivate,
}: PlatformDeploymentOverviewSectionProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <article className="panel card-stack">
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
                  <div className="platform-inline-meta">
                    <Link className="status-text" to={`/control/platform/providers/${binding.provider.id}`}>
                      {binding.provider.slug}
                    </Link>
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
                    <div className="platform-inline-meta">
                      <span className="status-text">{binding.configuration_status?.summary ?? t("platformControl.summary.none")}</span>
                    </div>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="platform-inline-meta">
        <button
          type="button"
          className="btn btn-primary"
          onClick={onActivate}
          disabled={deployment.is_active || activating}
        >
          {deployment.is_active
            ? t("platformControl.actions.active")
            : activating
              ? t("platformControl.actions.activating")
              : t("platformControl.actions.activate")}
        </button>
      </div>
    </article>
  );
}
