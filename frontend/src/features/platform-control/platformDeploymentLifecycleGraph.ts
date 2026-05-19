import type { TFunction } from "i18next";
import type { PlatformDeploymentProfile } from "../../api/platform";
import { buildLifecycleGraphDefinition, type LifecycleGraphDefinition, type LifecycleTransitionDefinition } from "../../components/LifecycleGraph";

export const PLATFORM_DEPLOYMENT_LIFECYCLE_STATE_IDS = [
  "incomplete",
  "ready_inactive",
  "active_ready",
  "active_degraded",
  "deleted",
] as const;

export type PlatformDeploymentLifecycleState = typeof PLATFORM_DEPLOYMENT_LIFECYCLE_STATE_IDS[number];

export const PLATFORM_DEPLOYMENT_LIFECYCLE_TRANSITIONS: LifecycleTransitionDefinition[] = [
  { from: "incomplete", to: "ready_inactive" },
  { from: "ready_inactive", to: "incomplete" },
  { from: "ready_inactive", to: "active_ready" },
  { from: "active_ready", to: "ready_inactive" },
  { from: "active_ready", to: "active_degraded" },
  { from: "active_degraded", to: "active_ready" },
  { from: "active_degraded", to: "ready_inactive" },
  { from: "incomplete", to: "deleted" },
  { from: "ready_inactive", to: "deleted" },
  { from: "active_ready", to: "deleted" },
  { from: "active_degraded", to: "deleted" },
];

export function createPlatformDeploymentLifecycleGraphDefinition(t: TFunction<"common">): LifecycleGraphDefinition {
  return buildLifecycleGraphDefinition(t, {
    artifactType: "platform-deployment",
    stateIds: PLATFORM_DEPLOYMENT_LIFECYCLE_STATE_IDS,
    i18nBase: "platformControl.deployments.lifecycle",
    positions: [
      { x: 90, y: 82 },
      { x: 285, y: 82 },
      { x: 480, y: 82 },
      { x: 480, y: 214 },
      { x: 675, y: 214 },
    ],
    transitions: PLATFORM_DEPLOYMENT_LIFECYCLE_TRANSITIONS,
  });
}

export function getPlatformDeploymentLifecycleState(
  deployment: PlatformDeploymentProfile,
): PlatformDeploymentLifecycleState {
  if (deployment.is_active) {
    return deployment.configuration_status?.is_ready === true ? "active_ready" : "active_degraded";
  }
  return deployment.configuration_status?.is_ready === true ? "ready_inactive" : "incomplete";
}

export function getPlatformDeploymentLifecycleSummary(
  t: TFunction<"common">,
  deployment: PlatformDeploymentProfile,
  activeDeployment?: PlatformDeploymentProfile | null,
): string {
  const activeStatus = deployment.is_active
    ? t("platformControl.badges.active")
    : t("platformControl.badges.inactive");
  const readinessStatus = deployment.configuration_status?.is_ready
    ? t("platformControl.badges.ready")
    : t("platformControl.badges.incomplete");
  const readinessSummary = deployment.configuration_status?.summary ?? t("platformControl.summary.none");
  const bindingCount = deployment.bindings.length;
  const readyBindingCount = deployment.bindings.filter((binding) => binding.configuration_status?.is_ready === true).length;
  const incompleteCapabilityCount =
    deployment.configuration_status?.incomplete_capabilities.length ??
    deployment.bindings.filter((binding) => binding.configuration_status?.is_ready !== true).length;
  const providerCount = new Set(deployment.bindings.map((binding) => binding.provider.id)).size;
  const resourceCount = deployment.bindings.reduce((total, binding) => total + binding.resources.length, 0);
  const activeDeploymentLabel = activeDeployment
    ? `${activeDeployment.display_name} (${activeDeployment.slug})`
    : t("platformControl.summary.none");

  return t("platformControl.deployments.lifecycle.summary", {
    activeStatus,
    readinessStatus,
    readinessSummary,
    bindingCount,
    readyBindingCount,
    incompleteCapabilityCount,
    providerCount,
    resourceCount,
    activeDeployment: activeDeploymentLabel,
  });
}
