import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { PlatformCapability, PlatformDeploymentProfile } from "../../../api/platform";
import { capabilityRequiresServedModel, summarizeBindingServedModels } from "../utils";

type PlatformCapabilitiesOverviewProps = {
  capabilities: PlatformCapability[];
  activeDeployment: PlatformDeploymentProfile | null;
  isRefreshing: boolean;
  onRefresh: () => void;
};

export default function PlatformCapabilitiesOverview({
  capabilities,
  activeDeployment,
  isRefreshing,
  onRefresh,
}: PlatformCapabilitiesOverviewProps): JSX.Element {
  const { t } = useTranslation("common");
  const bindingByCapability = new Map(activeDeployment?.bindings.map((binding) => [binding.capability, binding]) ?? []);

  return (
    <article className="panel card-stack">
      <div className="platform-section-header">
        <div className="status-row">
          <h3 className="section-title">{t("platformControl.sections.capabilities")}</h3>
          <p className="status-text">{t("platformControl.capabilities.description")}</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={onRefresh} disabled={isRefreshing}>
          {isRefreshing ? t("platformControl.actions.refreshing") : t("platformControl.actions.refresh")}
        </button>
      </div>

      {capabilities.length === 0 ? (
        <p className="status-text">{t("platformControl.capabilities.empty")}</p>
      ) : (
        <div className="platform-capability-grid">
          {capabilities.map((capability) => {
            const binding = bindingByCapability.get(capability.capability);
            const provider = capability.active_provider;
            return (
              <article key={capability.capability} className="platform-capability-card">
                <div className="platform-card-header">
                  <div className="status-row">
                    <h4 className="section-title">{capability.display_name}</h4>
                    <span className="platform-badge" data-tone={capability.required ? "required" : "active"}>
                      {capability.required ? t("platformControl.badges.required") : t("platformControl.badges.optional")}
                    </span>
                  </div>
                </div>
                <p className="status-text">{capability.description}</p>
                {provider ? (
                  <>
                    <div className="status-row">
                      <span className="field-label">{t("platformControl.capabilities.activeProvider")}</span>
                      <strong>{provider.display_name}</strong>
                      <span className="status-text">
                        <code className="code-inline">{provider.slug}</code>
                      </span>
                    </div>
                    {binding ? (
                      <>
                        <div className="status-row">
                          <span className="field-label">{t("platformControl.capabilities.runtime")}</span>
                          <span className="status-text">{binding.provider.adapter_kind}</span>
                        </div>
                        {capabilityRequiresServedModel(capability.capability) ? (
                          <div className="status-row">
                            <span className="field-label">{t("platformControl.capabilities.servedArtifacts")}</span>
                            <span className="status-text">
                              {summarizeBindingServedModels(binding, t("platformControl.summary.none"))}
                            </span>
                          </div>
                        ) : null}
                      </>
                    ) : null}
                    <div className="platform-inline-meta">
                      <Link className="btn btn-secondary" to={`/control/platform/providers/${provider.id}`}>
                        {t("platformControl.actions.openProvider")}
                      </Link>
                      {activeDeployment ? (
                        <Link className="btn btn-secondary" to={`/control/platform/deployments/${activeDeployment.id}`}>
                          {t("platformControl.actions.openDeployment")}
                        </Link>
                      ) : null}
                    </div>
                  </>
                ) : (
                  <>
                    <p className="status-text">{t("platformControl.capabilities.unbound")}</p>
                    <div className="platform-inline-meta">
                      <Link className="btn btn-secondary" to="/control/platform/deployments">
                        {t("platformControl.actions.viewDeployments")}
                      </Link>
                    </div>
                  </>
                )}
              </article>
            );
          })}
        </div>
      )}
    </article>
  );
}
