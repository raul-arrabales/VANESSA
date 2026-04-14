import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { PlatformCapability, PlatformDeploymentProfile } from "../../../api/platform";
import { capabilityRequiresModelResource } from "../capabilities";
import { summarizeBindingResources } from "../platformTopology";

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
        <div className="platform-capability-grid platform-capability-list">
          {capabilities.map((capability) => {
            const binding = bindingByCapability.get(capability.capability);
            const provider = capability.active_provider;
            return (
              <article key={capability.capability} className="platform-capability-card platform-capability-row">
                <div className="platform-capability-summary">
                  <div className="status-row">
                    <h4 className="section-title">{capability.display_name}</h4>
                    <span className="platform-badge" data-tone={capability.required ? "required" : "active"}>
                      {capability.required ? t("platformControl.badges.required") : t("platformControl.badges.optional")}
                    </span>
                  </div>
                  <p className="status-text platform-capability-description">{capability.description}</p>
                </div>
                {provider ? (
                  <>
                    <div className="platform-capability-details">
                      <div className="platform-capability-detail">
                        <span className="field-label">{t("platformControl.capabilities.activeProvider")}</span>
                        <span className="platform-capability-value">
                          <strong>{provider.display_name}</strong>{" "}
                          <code className="code-inline platform-capability-code" title={provider.slug}>
                            {provider.slug}
                          </code>
                        </span>
                      </div>
                      {binding ? (
                        <>
                          <div className="platform-capability-detail">
                            <span className="field-label">{t("platformControl.capabilities.runtime")}</span>
                            <span className="platform-capability-value">{binding.provider.adapter_kind}</span>
                          </div>
                          {capabilityRequiresModelResource(capability.capability) ? (
                            <div className="platform-capability-detail">
                              <span className="field-label">{t("platformControl.capabilities.servedArtifacts")}</span>
                              <span className="platform-capability-value">
                                {summarizeBindingResources(binding, t("platformControl.summary.none"))}
                              </span>
                            </div>
                          ) : null}
                        </>
                      ) : null}
                    </div>
                    <div className="inline-meta-list platform-capability-actions">
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
                    <p className="status-text platform-capability-value">{t("platformControl.capabilities.unbound")}</p>
                    <div className="inline-meta-list platform-capability-actions">
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
