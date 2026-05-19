import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import ActionIcon from "../../../components/ActionIcon";
import IconButton from "../../../components/IconButton";
import IconLink from "../../../components/IconLink";
import { LifecycleGraphActionModal, useSelectedLifecycleItem } from "../../../components/lifecycle-graph";
import type { PlatformCapability, PlatformDeploymentProfile } from "../../../api/platform";
import {
  createPlatformDeploymentLifecycleGraphDefinition,
  getPlatformDeploymentLifecycleState,
  getPlatformDeploymentLifecycleSummaryRows,
} from "../platformDeploymentLifecycleGraph";
import { summarizeBindingResources } from "../platformTopology";

type PlatformDeploymentsDirectoryProps = {
  deployments: PlatformDeploymentProfile[];
  capabilities: PlatformCapability[];
  activeDeployment?: PlatformDeploymentProfile | null;
};

export default function PlatformDeploymentsDirectory({
  deployments,
  capabilities,
  activeDeployment = null,
}: PlatformDeploymentsDirectoryProps): JSX.Element {
  const { t } = useTranslation("common");
  const { selectedLifecycleItem, openLifecycleItem, closeLifecycleItem } = useSelectedLifecycleItem<PlatformDeploymentProfile>();
  const [expandedDeploymentIds, setExpandedDeploymentIds] = useState<Set<string>>(() => new Set());
  const lifecycleDefinition = useMemo(() => createPlatformDeploymentLifecycleGraphDefinition(t), [t]);
  const capabilityLabelByKey = new Map(capabilities.map((capability) => [capability.capability, capability.display_name]));

  function toggleDeployment(deploymentId: string): void {
    setExpandedDeploymentIds((current) => {
      const next = new Set(current);
      if (next.has(deploymentId)) {
        next.delete(deploymentId);
      } else {
        next.add(deploymentId);
      }
      return next;
    });
  }

  if (deployments.length === 0) {
    return <p className="status-text">{t("platformControl.deployments.empty")}</p>;
  }

  return (
    <div className="platform-deployment-list">
      {deployments.map((deployment) => {
        const isExpanded = expandedDeploymentIds.has(deployment.id);
        const bindingsPanelId = `deployment-bindings-${deployment.id}`;
        const toggleLabel = t(
          isExpanded
            ? "platformControl.deployments.collapseCapabilities"
            : "platformControl.deployments.expandCapabilities",
          { name: deployment.display_name },
        );
        return (
          <article key={deployment.id} className="platform-deployment-card" data-expanded={isExpanded ? "true" : "false"}>
            <div className="platform-card-header platform-deployment-card-header">
              <div className="platform-deployment-summary">
                <div className="platform-deployment-title-row">
                  <h3 className="section-title">{deployment.display_name}</h3>
                  <span className="status-text">
                    <code className="code-inline">{deployment.slug}</code>
                  </span>
                </div>
                <p className="status-text">{deployment.description || t("platformControl.deployments.noDescription")}</p>
                <div className="inline-meta-list platform-deployment-state-row">
                  <span className="platform-badge" data-tone={deployment.is_active ? "active" : "inactive"}>
                    {deployment.is_active ? t("platformControl.badges.active") : t("platformControl.badges.inactive")}
                  </span>
                  {deployment.configuration_status ? (
                    <span className="platform-badge" data-tone={deployment.configuration_status.is_ready ? "enabled" : "inactive"}>
                      {deployment.configuration_status.is_ready
                        ? t("platformControl.badges.ready")
                        : t("platformControl.badges.incomplete")}
                    </span>
                  ) : null}
                  <span className="platform-badge" data-tone="local">
                    {t("platformControl.deployments.bindingCount", { count: deployment.bindings.length })}
                  </span>
                  {deployment.configuration_status ? (
                    <span className="status-text platform-deployment-readiness">{deployment.configuration_status.summary}</span>
                  ) : null}
                </div>
              </div>
              <div className="inline-meta-list platform-deployment-actions">
                <IconButton
                  label={toggleLabel}
                  aria-controls={bindingsPanelId}
                  aria-expanded={isExpanded}
                  onClick={() => toggleDeployment(deployment.id)}
                >
                  <ActionIcon name={isExpanded ? "collapse" : "expand"} />
                </IconButton>
                <IconButton
                  label={t("platformControl.deployments.lifecycle.actionLabel", { name: deployment.display_name })}
                  onClick={() => openLifecycleItem(deployment)}
                >
                  <ActionIcon name="lifecycle" />
                </IconButton>
                <IconLink
                  to={`/control/platform/deployments/${deployment.id}`}
                  label={t("platformControl.actions.openDeploymentFor", { name: deployment.display_name })}
                >
                  <ActionIcon name="open" />
                </IconLink>
              </div>
            </div>
            {isExpanded ? (
              <div id={bindingsPanelId} className="platform-deployment-bindings">
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
              </div>
            ) : null}
          </article>
        );
      })}
      <LifecycleGraphActionModal
        item={selectedLifecycleItem}
        getTitle={(deployment) => t("platformControl.deployments.lifecycle.modalTitle", { name: deployment.display_name })}
        description={t("platformControl.deployments.lifecycle.modalDescription")}
        definition={lifecycleDefinition}
        getCurrentState={getPlatformDeploymentLifecycleState}
        getSummaryRows={(deployment) => getPlatformDeploymentLifecycleSummaryRows(t, deployment, activeDeployment)}
        currentLabel={t("platformControl.deployments.lifecycle.currentState")}
        unknownLabel={t("platformControl.summary.unknown")}
        closeLabel={t("platformControl.actions.cancel")}
        onClose={closeLifecycleItem}
      />
    </div>
  );
}
