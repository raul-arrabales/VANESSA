import type { PlatformDeploymentProfile } from "../../api/platform";

export type DeploymentDetailRouteState = {
  deploymentSeed?: PlatformDeploymentProfile;
};

export function withDeploymentSeedState(
  deployment: PlatformDeploymentProfile,
  currentState?: unknown,
): Record<string, unknown> {
  const baseState = currentState && typeof currentState === "object" && !Array.isArray(currentState)
    ? { ...(currentState as Record<string, unknown>) }
    : {};
  return {
    ...baseState,
    deploymentSeed: deployment,
  };
}

export function readDeploymentSeedFromState(
  state: unknown,
  deploymentId?: string,
): PlatformDeploymentProfile | null {
  if (!state || typeof state !== "object" || Array.isArray(state)) {
    return null;
  }

  const rawDeployment = (state as Record<string, unknown>).deploymentSeed;
  if (!rawDeployment || typeof rawDeployment !== "object" || Array.isArray(rawDeployment)) {
    return null;
  }

  const deployment = rawDeployment as PlatformDeploymentProfile;
  if (typeof deployment.id !== "string" || !deployment.id.trim()) {
    return null;
  }
  if (deploymentId && deployment.id !== deploymentId) {
    return null;
  }

  return deployment;
}
