import type { TFunction } from "i18next";
import type { PlatformDeploymentProfile, PlatformProvider, PlatformProviderFamily } from "../../api/platform";
import type { LifecycleGraphDefinition, LifecycleTransitionDefinition } from "../../components/LifecycleGraph";
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
  return {
    artifactType: "platform-provider",
    states: PLATFORM_PROVIDER_LIFECYCLE_STATE_IDS.map((stateId, index) => ({
      id: stateId,
      label: t(`platformControl.providers.lifecycle.states.${stateId}`),
      x: [90, 255, 420, 585, 420, 675][index],
      y: [82, 82, 82, 82, 214, 214][index],
    })),
    transitions: PLATFORM_PROVIDER_LIFECYCLE_TRANSITIONS.map((transition) => ({
      ...transition,
      label: t(`platformControl.providers.lifecycle.transitions.${transition.from}.${transition.to}`),
    })),
  };
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

export function getPlatformProviderLifecycleSummary(
  t: TFunction<"common">,
  provider: PlatformProvider,
  deployments: PlatformDeploymentProfile[],
  providerFamily?: PlatformProviderFamily | null,
  activeDeployment: PlatformDeploymentProfile | null = getActiveDeployment(deployments),
): string {
  const usageEntries = getProviderUsageEntries(provider.id, deployments);
  const usesActiveDeployment = usageEntries.some((entry) => entry.deployment.is_active);
  const loadedResource =
    provider.loaded_managed_model_name ??
    provider.loaded_runtime_model_id ??
    provider.loaded_local_path ??
    provider.loaded_source_id ??
    t("platformControl.summary.none");
  const loadError = provider.load_error
    ? t("platformControl.providers.lifecycle.loadErrorSuffix", { error: provider.load_error })
    : "";

  return t("platformControl.providers.lifecycle.summary", {
    enabledStatus: provider.enabled ? t("platformControl.badges.enabled") : t("platformControl.badges.disabled"),
    origin: t(`platformControl.badges.${provider.provider_origin}`),
    capability: provider.capability,
    providerFamily: providerFamily?.display_name ?? provider.provider_key,
    adapter: provider.adapter_kind,
    usageCount: usageEntries.length,
    activeUsage: usesActiveDeployment
      ? t("platformControl.providers.activeReference")
      : t("platformControl.providers.inactiveReference"),
    activeDeployment: activeDeployment
      ? `${activeDeployment.display_name} (${activeDeployment.slug})`
      : t("platformControl.summary.none"),
    loadState: provider.load_state ?? t("platformControl.summary.none"),
    loadedResource,
    endpoint: provider.endpoint_url,
    loadError,
  });
}
