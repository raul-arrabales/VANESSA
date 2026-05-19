import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import ActionIcon from "../../../components/ActionIcon";
import IconButton from "../../../components/IconButton";
import { LifecycleGraphActionModal } from "../../../components/LifecycleGraph";
import type { PlatformDeploymentProfile, PlatformProvider, PlatformProviderFamily } from "../../../api/platform";
import {
  createPlatformProviderLifecycleGraphDefinition,
  getPlatformProviderLifecycleState,
  getPlatformProviderLifecycleSummary,
} from "../platformProviderLifecycleGraph";

type PlatformProviderOverviewSectionProps = {
  activeDeployment: PlatformDeploymentProfile | null;
  deployments?: PlatformDeploymentProfile[];
  isUsedByActiveDeployment: boolean;
  provider: PlatformProvider;
  providerFamily: PlatformProviderFamily | null;
};

export default function PlatformProviderOverviewSection({
  activeDeployment,
  deployments = activeDeployment ? [activeDeployment] : [],
  isUsedByActiveDeployment,
  provider,
  providerFamily,
}: PlatformProviderOverviewSectionProps): JSX.Element {
  const { t } = useTranslation("common");
  const [isLifecycleModalOpen, setIsLifecycleModalOpen] = useState(false);
  const lifecycleDefinition = useMemo(() => createPlatformProviderLifecycleGraphDefinition(t), [t]);

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
          <IconButton
            label={t("platformControl.providers.lifecycle.actionLabel", { name: provider.display_name })}
            onClick={() => setIsLifecycleModalOpen(true)}
          >
            <ActionIcon name="lifecycle" />
          </IconButton>
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
      <LifecycleGraphActionModal
        item={isLifecycleModalOpen ? provider : null}
        getTitle={(selectedProvider) => t("platformControl.providers.lifecycle.modalTitle", { name: selectedProvider.display_name })}
        description={t("platformControl.providers.lifecycle.modalDescription")}
        definition={lifecycleDefinition}
        getCurrentState={(selectedProvider) => getPlatformProviderLifecycleState(selectedProvider, deployments)}
        getSupportingText={(selectedProvider) => getPlatformProviderLifecycleSummary(t, selectedProvider, deployments, providerFamily, activeDeployment)}
        currentLabel={t("platformControl.providers.lifecycle.currentState")}
        unknownLabel={t("platformControl.summary.unknown")}
        closeLabel={t("platformControl.actions.cancel")}
        onClose={() => setIsLifecycleModalOpen(false)}
      />
    </article>
  );
}
