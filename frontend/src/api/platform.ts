import { ApiError } from "../auth/authApi";

const backendBaseUrl = (import.meta.env.VITE_BACKEND_BASE_URL as string | undefined)?.trim() || "/api";

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  token?: string;
};

export type PlatformCapability = {
  capability: string;
  display_name: string;
  description: string;
  required: boolean;
  active_provider: {
    id: string;
    slug: string;
    provider_key: string;
    provider_origin?: "local" | "cloud";
    display_name: string;
    deployment_profile_id: string;
    deployment_profile_slug: string;
  } | null;
};

export type PlatformProvider = {
  id: string;
  slug: string;
  provider_key: string;
  provider_origin: "local" | "cloud";
  capability: string;
  adapter_kind: string;
  display_name: string;
  description: string;
  endpoint_url: string;
  healthcheck_url?: string | null;
  enabled: boolean;
  config: Record<string, unknown>;
  secret_refs: Record<string, string>;
  loaded_managed_model_id?: string | null;
  loaded_managed_model_name?: string | null;
  loaded_runtime_model_id?: string | null;
  loaded_local_path?: string | null;
  loaded_source_id?: string | null;
  load_state?: "empty" | "loading" | "reconciling" | "loaded" | "error" | string;
  load_error?: string | null;
};

export type PlatformProviderFamily = {
  provider_key: string;
  provider_origin: "local" | "cloud";
  capability: string;
  adapter_kind: string;
  display_name: string;
  description: string;
};

export type PlatformDeploymentBinding = {
  capability: string;
  provider: {
    id: string;
    slug: string;
    provider_key: string;
    provider_origin?: "local" | "cloud";
    display_name: string;
    endpoint_url: string;
    enabled: boolean;
    adapter_kind: string;
  };
  resources: Array<{
    id: string;
    resource_kind?: string | null;
    ref_type?: string | null;
    managed_model_id?: string | null;
    knowledge_base_id?: string | null;
    provider_resource_id?: string | null;
    display_name?: string | null;
    metadata?: Record<string, unknown>;
  }>;
  default_resource_id?: string | null;
  default_resource?: {
    id: string;
    resource_kind?: string | null;
    ref_type?: string | null;
    managed_model_id?: string | null;
    knowledge_base_id?: string | null;
    provider_resource_id?: string | null;
    display_name?: string | null;
    metadata?: Record<string, unknown>;
  } | null;
  resource_policy?: Record<string, unknown>;
  config: Record<string, unknown>;
  configuration_status?: {
    is_ready: boolean;
    issues: Array<{
      code: string;
      message: string;
    }>;
    summary: string;
  };
};

export type PlatformDeploymentProfile = {
  id: string;
  slug: string;
  display_name: string;
  description: string;
  is_active: boolean;
  bindings: PlatformDeploymentBinding[];
  configuration_status?: {
    is_ready: boolean;
    incomplete_capabilities: string[];
    summary: string;
  };
};

export type PlatformActivationAuditEntry = {
  id: string;
  deployment_profile: {
    id: string;
    slug: string;
    display_name: string;
  };
  previous_deployment_profile: {
    id: string;
    slug: string;
    display_name: string;
  } | null;
  activated_by_user_id: number | null;
  activated_at: string;
};

export type PlatformProviderValidation = {
  provider: Pick<PlatformProvider, "id" | "slug">;
  validation: {
    health: {
      reachable: boolean;
      status_code: number;
    };
    embeddings_reachable?: boolean;
    embeddings_status_code?: number;
    embedding_dimension?: number;
    resources_reachable?: boolean;
    resources_status_code?: number;
    resources?: Array<{
      id: string;
      resource_kind?: string | null;
      ref_type?: string | null;
      managed_model_id?: string | null;
      knowledge_base_id?: string | null;
      provider_resource_id?: string | null;
      display_name?: string | null;
      metadata?: Record<string, unknown>;
    }>;
    credential?: {
      id: string;
      provider: string;
      display_name: string;
      api_base_url?: string | null;
    };
    binding_error?: string;
    resource_errors?: Array<{
      code: string;
      resource_id?: string | null;
      provider_resource_id?: string | null;
      message?: string | null;
    }>;
  };
};

export type PlatformProviderMutationInput = {
  provider_key: string;
  slug: string;
  display_name: string;
  description: string;
  endpoint_url: string;
  healthcheck_url?: string | null;
  enabled: boolean;
  config: Record<string, unknown>;
  secret_refs: Record<string, string>;
};

export type PlatformDeploymentMutationInput = {
  slug: string;
  display_name: string;
  description: string;
  bindings: Array<{
    capability: string;
    provider_id: string;
    resources?: Array<{
      id: string;
      resource_kind?: string | null;
      ref_type?: string | null;
      managed_model_id?: string | null;
      provider_resource_id?: string | null;
      display_name?: string | null;
      metadata?: Record<string, unknown>;
    }>;
    default_resource_id?: string | null;
    resource_policy?: Record<string, unknown>;
    config?: Record<string, unknown>;
  }>;
};

export type PlatformDeploymentIdentityMutationInput = Pick<
  PlatformDeploymentMutationInput,
  "slug" | "display_name" | "description"
>;

export type PlatformDeploymentBindingMutationInput = {
  provider_id: string;
  resources?: Array<{
    id: string;
    resource_kind?: string | null;
    ref_type?: string | null;
    managed_model_id?: string | null;
    knowledge_base_id?: string | null;
    provider_resource_id?: string | null;
    display_name?: string | null;
    metadata?: Record<string, unknown>;
  }>;
  default_resource_id?: string | null;
  resource_policy?: Record<string, unknown>;
  config?: Record<string, unknown>;
};

function buildUrl(path: string): string {
  return `${backendBaseUrl.replace(/\/$/, "")}${path}`;
}

async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: HeadersInit = {
    Accept: "application/json",
  };

  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }

  const response = await fetch(buildUrl(path), {
    method: options.method ?? "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  const rawBody = await response.text();
  let payload: Record<string, unknown> = {};
  if (rawBody) {
    try {
      payload = JSON.parse(rawBody) as Record<string, unknown>;
    } catch {
      if (!response.ok) {
        throw new ApiError(`HTTP ${response.status}`, response.status);
      }
      throw new ApiError(
        "Backend returned a non-JSON response",
        response.status,
        "invalid_response_format",
      );
    }
  }

  if (!response.ok) {
    const message = String(payload.message ?? payload.error ?? `HTTP ${response.status}`);
    const code = payload.error ? String(payload.error) : undefined;
    throw new ApiError(message, response.status, code);
  }

  return payload as T;
}

export async function listPlatformCapabilities(token: string): Promise<PlatformCapability[]> {
  const result = await requestJson<{ capabilities: PlatformCapability[] }>("/v1/platform/capabilities", { token });
  return result.capabilities;
}

export async function listPlatformProviders(token: string): Promise<PlatformProvider[]> {
  const result = await requestJson<{ providers: PlatformProvider[] }>("/v1/platform/providers", { token });
  return result.providers;
}

export async function listPlatformProviderFamilies(token: string): Promise<PlatformProviderFamily[]> {
  const result = await requestJson<{ provider_families: PlatformProviderFamily[] }>("/v1/platform/provider-families", { token });
  return result.provider_families;
}

export async function listPlatformDeployments(token: string): Promise<PlatformDeploymentProfile[]> {
  const result = await requestJson<{ deployments: PlatformDeploymentProfile[] }>("/v1/platform/deployments", { token });
  return result.deployments;
}

export async function listPlatformActivationAudit(token: string): Promise<PlatformActivationAuditEntry[]> {
  const result = await requestJson<{ activation_audit: PlatformActivationAuditEntry[] }>("/v1/platform/activation-audit", { token });
  return result.activation_audit;
}

export async function validatePlatformProvider(
  providerId: string,
  token: string,
  options: { credentialId?: string } = {},
): Promise<PlatformProviderValidation> {
  return requestJson<PlatformProviderValidation>(`/v1/platform/providers/${encodeURIComponent(providerId)}/validate`, {
    method: "POST",
    token,
    body: options.credentialId ? { credential_id: options.credentialId } : undefined,
  });
}

export async function createPlatformProvider(
  input: PlatformProviderMutationInput,
  token: string,
): Promise<PlatformProvider> {
  const result = await requestJson<{ provider: PlatformProvider }>("/v1/platform/providers", {
    method: "POST",
    token,
    body: input,
  });
  return result.provider;
}

export async function updatePlatformProvider(
  providerId: string,
  input: Omit<PlatformProviderMutationInput, "provider_key">,
  token: string,
): Promise<PlatformProvider> {
  const result = await requestJson<{ provider: PlatformProvider }>(`/v1/platform/providers/${encodeURIComponent(providerId)}`, {
    method: "PUT",
    token,
    body: input,
  });
  return result.provider;
}

export async function deletePlatformProvider(providerId: string, token: string): Promise<void> {
  await requestJson<{ deleted: boolean }>(`/v1/platform/providers/${encodeURIComponent(providerId)}`, {
    method: "DELETE",
    token,
  });
}

export async function assignPlatformProviderLoadedModel(
  providerId: string,
  managedModelId: string,
  token: string,
): Promise<PlatformProvider> {
  const result = await requestJson<{ provider: PlatformProvider }>(
    `/v1/platform/providers/${encodeURIComponent(providerId)}/loaded-model`,
    {
      method: "POST",
      token,
      body: { managed_model_id: managedModelId },
    },
  );
  return result.provider;
}

export async function clearPlatformProviderLoadedModel(
  providerId: string,
  token: string,
): Promise<PlatformProvider> {
  const result = await requestJson<{ provider: PlatformProvider }>(
    `/v1/platform/providers/${encodeURIComponent(providerId)}/loaded-model`,
    {
      method: "DELETE",
      token,
    },
  );
  return result.provider;
}

export async function activateDeploymentProfile(deploymentId: string, token: string): Promise<PlatformDeploymentProfile> {
  const result = await requestJson<{ deployment_profile: PlatformDeploymentProfile }>(
    `/v1/platform/deployments/${encodeURIComponent(deploymentId)}/activate`,
    {
      method: "POST",
      token,
    },
  );
  return result.deployment_profile;
}

export async function createDeploymentProfile(
  input: PlatformDeploymentMutationInput,
  token: string,
): Promise<PlatformDeploymentProfile> {
  const result = await requestJson<{ deployment_profile: PlatformDeploymentProfile }>("/v1/platform/deployments", {
    method: "POST",
    token,
    body: input,
  });
  return result.deployment_profile;
}

export async function updateDeploymentProfile(
  deploymentId: string,
  input: PlatformDeploymentMutationInput,
  token: string,
): Promise<PlatformDeploymentProfile> {
  const result = await requestJson<{ deployment_profile: PlatformDeploymentProfile }>(
    `/v1/platform/deployments/${encodeURIComponent(deploymentId)}`,
    {
      method: "PUT",
      token,
      body: input,
    },
  );
  return result.deployment_profile;
}

export async function patchDeploymentProfileIdentity(
  deploymentId: string,
  input: PlatformDeploymentIdentityMutationInput,
  token: string,
): Promise<PlatformDeploymentProfile> {
  const result = await requestJson<{ deployment_profile: PlatformDeploymentProfile }>(
    `/v1/platform/deployments/${encodeURIComponent(deploymentId)}`,
    {
      method: "PATCH",
      token,
      body: input,
    },
  );
  return result.deployment_profile;
}

export async function upsertDeploymentBinding(
  deploymentId: string,
  capability: string,
  input: PlatformDeploymentBindingMutationInput,
  token: string,
): Promise<PlatformDeploymentProfile> {
  const result = await requestJson<{ deployment_profile: PlatformDeploymentProfile }>(
    `/v1/platform/deployments/${encodeURIComponent(deploymentId)}/bindings/${encodeURIComponent(capability)}`,
    {
      method: "PUT",
      token,
      body: input,
    },
  );
  return result.deployment_profile;
}

export async function cloneDeploymentProfile(
  deploymentId: string,
  input: Pick<PlatformDeploymentMutationInput, "slug" | "display_name" | "description">,
  token: string,
): Promise<PlatformDeploymentProfile> {
  const result = await requestJson<{ deployment_profile: PlatformDeploymentProfile }>(
    `/v1/platform/deployments/${encodeURIComponent(deploymentId)}/clone`,
    {
      method: "POST",
      token,
      body: input,
    },
  );
  return result.deployment_profile;
}

export async function deleteDeploymentProfile(deploymentId: string, token: string): Promise<void> {
  await requestJson<{ deleted: boolean }>(`/v1/platform/deployments/${encodeURIComponent(deploymentId)}`, {
    method: "DELETE",
    token,
  });
}
