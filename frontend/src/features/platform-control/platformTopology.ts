import type {
  PlatformDeploymentBinding,
  PlatformDeploymentProfile,
} from "../../api/platform";

export function getModelDisplayName(model: { id: string; name?: string | null }): string {
  return model.name?.trim() || model.id;
}

export function summarizeResources(
  resources: Array<{ id: string; display_name?: string | null; metadata?: Record<string, unknown> }> | undefined,
  defaultResource: { id: string; display_name?: string | null; metadata?: Record<string, unknown> } | null | undefined,
  noneLabel: string,
): string {
  const items = resources ?? [];
  if (!defaultResource && items.length === 0) {
    return noneLabel;
  }

  const primary = defaultResource ?? items[0];
  if (!primary) {
    return noneLabel;
  }

  const primaryLabel = primary.display_name?.trim() || String(primary.metadata?.name ?? primary.id);
  const additionalCount = Math.max(items.length - 1, 0);
  if (additionalCount === 0) {
    return primaryLabel;
  }
  return `${primaryLabel} (+${additionalCount})`;
}

export function summarizeBindingResources(binding: PlatformDeploymentBinding, noneLabel: string): string {
  return summarizeResources(binding.resources, binding.default_resource, noneLabel);
}

export function getActiveDeployment(
  deployments: PlatformDeploymentProfile[],
): PlatformDeploymentProfile | null {
  return deployments.find((deployment) => deployment.is_active) ?? null;
}

export function getProviderUsageEntries(
  providerId: string,
  deployments: PlatformDeploymentProfile[],
): Array<{
  deployment: PlatformDeploymentProfile;
  bindings: PlatformDeploymentBinding[];
}> {
  return deployments
    .map((deployment) => ({
      deployment,
      bindings: deployment.bindings.filter((binding) => binding.provider.id === providerId),
    }))
    .filter((entry) => entry.bindings.length > 0);
}
