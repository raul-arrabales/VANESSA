import type { TFunction } from "i18next";
import type { PlatformDeploymentProfile, PlatformProvider, PlatformProviderFamily } from "../../api/platform";
import { buildLifecycleGraphDefinition, type LifecycleGraphDefinition, type LifecycleSummaryRow, type LifecycleTransitionDefinition } from "../../components/lifecycle-graph";
import { getActiveDeployment, getProviderUsageEntries } from "./platformTopology";

const ACTIVE_ATTENTION_LOAD_STATES = new Set(["empty", "loading", "reconciling", "error"]);

export const PLATFORM_PROVIDER_LIFECYCLE_STATE_IDS = [
  "disabled",
  "enabled_unbound",
  "bound_inactive",
  "active_ready",
  "active_attention",
  "deleted",
] as const;

export type PlatformProviderLifecycleState = typeof PLATFORM_PROVIDER_LIFECYCLE_STATE_IDS[number];

export const PLATFORM_PROVIDER_LIFECYCLE_TRANSITIONS: LifecycleTransitionDefinition[] = [
  { from: "disabled", to: "enabled_unbound" },
  { from: "enabled_unbound", to: "disabled" },
  { from: "enabled_unbound", to: "bound_inactive" },
  { from: "bound_inactive", to: "enabled_unbound" },
  { from: "bound_inactive", to: "active_ready" },
  { from: "active_ready", to: "bound_inactive" },
  { from: "active_ready", to: "active_attention" },
  { from: "active_attention", to: "active_ready" },
  { from: "active_attention", to: "bound_inactive" },
  { from: "disabled", to: "deleted" },
  { from: "enabled_unbound", to: "deleted" },
  { from: "bound_inactive", to: "deleted" },
  { from: "active_ready", to: "deleted" },
  { from: "active_attention", to: "deleted" },
];

export function createPlatformProviderLifecycleGraphDefinition(t: TFunction<"common">): LifecycleGraphDefinition {
  return buildLifecycleGraphDefinition(t, {
    artifactType: "platform-provider",
    stateIds: PLATFORM_PROVIDER_LIFECYCLE_STATE_IDS,
    i18nBase: "platformControl.providers.lifecycle",
    positions: [
      { x: 90, y: 82 },
      { x: 255, y: 82 },
      { x: 420, y: 82 },
      { x: 585, y: 82 },
      { x: 420, y: 214 },
      { x: 675, y: 214 },
    ],
    transitions: PLATFORM_PROVIDER_LIFECYCLE_TRANSITIONS,
  });
}

export function getPlatformProviderLifecycleState(
  provider: PlatformProvider,
  deployments: PlatformDeploymentProfile[],
): PlatformProviderLifecycleState {
  if (!provider.enabled) {
    return "disabled";
  }

  const usageEntries = getProviderUsageEntries(provider.id, deployments);
  if (usageEntries.length === 0) {
    return "enabled_unbound";
  }

  const usesActiveDeployment = usageEntries.some((entry) => entry.deployment.is_active);
  if (!usesActiveDeployment) {
    return "bound_inactive";
  }

  const loadState = provider.load_state?.trim().toLowerCase();
  return loadState && ACTIVE_ATTENTION_LOAD_STATES.has(loadState) ? "active_attention" : "active_ready";
}

export function getPlatformProviderLifecycleSummaryRows(
  t: TFunction<"common">,
  provider: PlatformProvider,
  deployments: PlatformDeploymentProfile[],
  providerFamily?: PlatformProviderFamily | null,
  activeDeployment: PlatformDeploymentProfile | null = getActiveDeployment(deployments),
): LifecycleSummaryRow[] {
  const usageEntries = getProviderUsageEntries(provider.id, deployments);
  const usesActiveDeployment = usageEntries.some((entry) => entry.deployment.is_active);
  const loadedResource =
    provider.loaded_managed_model_name ??
    provider.loaded_runtime_model_id ??
    provider.loaded_local_path ??
    provider.loaded_source_id ??
    t("platformControl.summary.none");
  const activeDeploymentLabel = activeDeployment
    ? `${activeDeployment.display_name} (${activeDeployment.slug})`
    : t("platformControl.summary.none");

  const rows: LifecycleSummaryRow[] = [
    { label: t("platformControl.providers.lifecycle.summaryLabels.status"), value: provider.enabled ? t("platformControl.badges.enabled") : t("platformControl.badges.disabled"), tone: provider.enabled ? "enabled" : "disabled" },
    { label: t("platformControl.providers.lifecycle.summaryLabels.origin"), value: t(`platformControl.badges.${provider.provider_origin}`) },
    { label: t("platformControl.providers.lifecycle.summaryLabels.capability"), value: provider.capability },
    { label: t("platformControl.providers.lifecycle.summaryLabels.family"), value: providerFamily?.display_name ?? provider.provider_key },
    { label: t("platformControl.providers.lifecycle.summaryLabels.adapter"), value: provider.adapter_kind },
    { label: t("platformControl.providers.lifecycle.summaryLabels.referencedDeployments"), value: usageEntries.length },
    {
      label: t("platformControl.providers.lifecycle.summaryLabels.activeUsage"),
      value: usesActiveDeployment
      ? t("platformControl.providers.activeReference")
      : t("platformControl.providers.inactiveReference"),
      tone: usesActiveDeployment ? "active" : "inactive",
    },
    { label: t("platformControl.providers.lifecycle.summaryLabels.activeDeployment"), value: activeDeploymentLabel },
    { label: t("platformControl.providers.lifecycle.summaryLabels.loadState"), value: provider.load_state ?? t("platformControl.summary.none") },
    { label: t("platformControl.providers.lifecycle.summaryLabels.loadedResource"), value: loadedResource },
    { label: t("platformControl.providers.lifecycle.summaryLabels.endpoint"), value: provider.endpoint_url },
  ];

  if (provider.load_error) {
    rows.push({
      label: t("platformControl.providers.lifecycle.summaryLabels.loadError"),
      value: provider.load_error,
      tone: "danger",
    });
  }

  return rows;
}
