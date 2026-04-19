import type { ManagedModel } from "../../api/modelops";
import type { PlatformProvider } from "../../api/platform";

export function modelMatchesProviderOrigin(model: ManagedModel, provider: PlatformProvider | null): boolean {
  if (!provider) {
    return true;
  }
  if (provider.provider_origin === "cloud") {
    return model.backend === "external_api" || model.hosting === "cloud";
  }
  return model.backend === "local" || model.hosting === "local";
}

export function filterModelsForProviderOrigin(
  models: ManagedModel[],
  provider: PlatformProvider | null,
): ManagedModel[] {
  return models.filter((model) => modelMatchesProviderOrigin(model, provider));
}
