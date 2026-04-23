import type { PlatformProvider, PlatformProviderFamily, PlatformProviderMutationInput } from "../../api/platform";

export const MODEL_CREDENTIAL_SECRET_REF_PREFIX = "modelops://credential/";
export type ProviderOrigin = PlatformProviderFamily["provider_origin"];
export type ProviderOriginSelection = ProviderOrigin | "";
export const PROVIDER_ORIGIN_OPTIONS: ReadonlyArray<{
  value: ProviderOrigin;
  labelKey: `platformControl.badges.${ProviderOrigin}`;
}> = [
  { value: "local", labelKey: "platformControl.badges.local" },
  { value: "cloud", labelKey: "platformControl.badges.cloud" },
] as const;

export type ProviderFormState = {
  providerKey: string;
  slug: string;
  displayName: string;
  description: string;
  endpointUrl: string;
  healthcheckUrl: string;
  enabled: boolean;
  credentialId: string;
  configText: string;
  secretRefsText: string;
};

export const DEFAULT_PROVIDER_FORM: ProviderFormState = {
  providerKey: "",
  slug: "",
  displayName: "",
  description: "",
  endpointUrl: "",
  healthcheckUrl: "",
  enabled: true,
  credentialId: "",
  configText: "{}",
  secretRefsText: "{}",
};

const OPENAI_COMPATIBLE_CLOUD_PROVIDER_KEYS = new Set([
  "openai_compatible_cloud_llm",
  "openai_compatible_cloud_embeddings",
]);

export const OPENAI_COMPATIBLE_CLOUD_PROVIDER_DEFAULTS = {
  endpointUrl: "https://api.openai.com/v1",
  healthcheckUrl: "None",
  configText: stringifyJson({
    models_path: "/models",
  }),
};

export function stringifyJson(value: Record<string, unknown> | Record<string, string>): string {
  return JSON.stringify(value, null, 2);
}

export function isOpenAICompatibleCloudProvider(providerKey: string): boolean {
  return OPENAI_COMPATIBLE_CLOUD_PROVIDER_KEYS.has(providerKey.trim().toLowerCase());
}

export function supportsSavedCredentials(providerKey: string): boolean {
  return isOpenAICompatibleCloudProvider(providerKey);
}

export function supportsLocalModelSlot(provider: Pick<PlatformProvider, "capability" | "provider_key"> | null): boolean {
  if (!provider) {
    return false;
  }
  return (provider.capability === "llm_inference" || provider.capability === "embeddings")
    && !isOpenAICompatibleCloudProvider(provider.provider_key);
}

export function applyProviderFamilyDefaults(form: ProviderFormState, providerKey: string): ProviderFormState {
  if (!isOpenAICompatibleCloudProvider(providerKey)) {
    return {
      ...form,
      providerKey,
    };
  }

  return {
    ...form,
    providerKey,
    ...OPENAI_COMPATIBLE_CLOUD_PROVIDER_DEFAULTS,
  };
}

export function getProviderFamily(
  providerFamilies: PlatformProviderFamily[],
  providerKey: string,
): PlatformProviderFamily | null {
  if (!providerKey) {
    return null;
  }
  return providerFamilies.find((family) => family.provider_key === providerKey) ?? null;
}

export function filterProviderFamiliesByOrigin(
  providerFamilies: PlatformProviderFamily[],
  selectedOrigin: ProviderOriginSelection,
): PlatformProviderFamily[] {
  if (!selectedOrigin) {
    return providerFamilies;
  }
  return providerFamilies.filter((family) => family.provider_origin === selectedOrigin);
}

export function resolveProviderOriginSelection(
  providerFamilies: PlatformProviderFamily[],
  providerKey: string,
): ProviderOriginSelection {
  return getProviderFamily(providerFamilies, providerKey)?.provider_origin ?? "";
}

export function applyProviderOriginChange(
  form: ProviderFormState,
  providerFamilies: PlatformProviderFamily[],
  nextOrigin: ProviderOriginSelection,
): ProviderFormState {
  const selectedFamily = getProviderFamily(providerFamilies, form.providerKey);
  if (!selectedFamily || !nextOrigin || selectedFamily.provider_origin === nextOrigin) {
    return form;
  }

  return {
    ...form,
    providerKey: "",
    endpointUrl: "",
    healthcheckUrl: "",
    credentialId: "",
    configText: stringifyJson({}),
    secretRefsText: updateSecretRefsCredential(form.secretRefsText, ""),
  };
}

export function normalizeOptionalUrl(value: string): string | null {
  const normalized = value.trim();
  if (!normalized || normalized.toLowerCase() === "none" || normalized.toLowerCase() === "null") {
    return null;
  }
  return normalized;
}

export function parseJsonObject(text: string, errorMessage: string): Record<string, unknown> {
  const normalized = text.trim();
  if (!normalized) {
    return {};
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(normalized);
  } catch {
    throw new Error(errorMessage);
  }

  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(errorMessage);
  }

  return parsed as Record<string, unknown>;
}

export function buildProviderMutationInput(
  form: ProviderFormState,
  options: {
    configErrorMessage: string;
    secretRefsErrorMessage: string;
  },
): PlatformProviderMutationInput {
  const config = parseJsonObject(form.configText, options.configErrorMessage);
  const secretRefs = parseJsonObject(form.secretRefsText, options.secretRefsErrorMessage) as Record<string, string>;
  return {
    provider_key: form.providerKey,
    slug: form.slug,
    display_name: form.displayName,
    description: form.description,
    endpoint_url: form.endpointUrl,
    healthcheck_url: normalizeOptionalUrl(form.healthcheckUrl),
    enabled: form.enabled,
    config,
    secret_refs: secretRefs,
  };
}

export function buildProviderUpdateMutationInput(
  form: ProviderFormState,
  options: {
    configErrorMessage: string;
    secretRefsErrorMessage: string;
  },
): Omit<PlatformProviderMutationInput, "provider_key"> {
  const input = buildProviderMutationInput(form, options);
  return {
    slug: input.slug,
    display_name: input.display_name,
    description: input.description,
    endpoint_url: input.endpoint_url,
    healthcheck_url: input.healthcheck_url,
    enabled: input.enabled,
    config: input.config,
    secret_refs: input.secret_refs,
  };
}

export function modelCredentialSecretRef(credentialId: string): string {
  return `${MODEL_CREDENTIAL_SECRET_REF_PREFIX}${credentialId.trim()}`;
}

export function credentialIdFromSecretRefs(secretRefs: Record<string, string>): string {
  const apiKeyRef = String(secretRefs.api_key ?? "").trim();
  if (apiKeyRef.startsWith(MODEL_CREDENTIAL_SECRET_REF_PREFIX)) {
    return apiKeyRef.slice(MODEL_CREDENTIAL_SECRET_REF_PREFIX.length).trim();
  }
  if (apiKeyRef.startsWith("modelops://")) {
    return apiKeyRef.slice("modelops://".length).trim();
  }
  return "";
}

export function updateSecretRefsCredential(text: string, credentialId: string): string {
  let secretRefs: Record<string, string> = {};
  try {
    const parsed = JSON.parse(text.trim() || "{}");
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      secretRefs = Object.fromEntries(
        Object.entries(parsed).map(([key, value]) => [key, String(value)]),
      );
    }
  } catch {
    secretRefs = {};
  }

  if (credentialId) {
    secretRefs.api_key = modelCredentialSecretRef(credentialId);
  } else if (credentialIdFromSecretRefs(secretRefs)) {
    delete secretRefs.api_key;
  }
  return stringifyJson(secretRefs);
}

export function buildProviderForm(provider: PlatformProvider): ProviderFormState {
  return {
    providerKey: provider.provider_key,
    slug: provider.slug,
    displayName: provider.display_name,
    description: provider.description,
    endpointUrl: provider.endpoint_url,
    healthcheckUrl: provider.healthcheck_url ?? "",
    enabled: provider.enabled,
    credentialId: credentialIdFromSecretRefs(provider.secret_refs),
    configText: stringifyJson(provider.config),
    secretRefsText: stringifyJson(provider.secret_refs),
  };
}
