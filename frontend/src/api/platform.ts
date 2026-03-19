import { ApiError } from "../auth/authApi";

const backendBaseUrl = (import.meta.env.VITE_BACKEND_BASE_URL as string | undefined)?.trim() || "/api";

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "DELETE";
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
    display_name: string;
    deployment_profile_id: string;
    deployment_profile_slug: string;
  } | null;
};

export type PlatformProvider = {
  id: string;
  slug: string;
  provider_key: string;
  capability: string;
  adapter_kind: string;
  display_name: string;
  description: string;
  endpoint_url: string;
  healthcheck_url?: string | null;
  enabled: boolean;
  config: Record<string, unknown>;
  secret_refs: Record<string, string>;
};

export type PlatformProviderFamily = {
  provider_key: string;
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
    display_name: string;
    endpoint_url: string;
    enabled: boolean;
    adapter_kind: string;
  };
  served_model_id?: string | null;
  served_model?: {
    id: string;
    name?: string | null;
    provider?: string | null;
    backend?: string | null;
    model_type?: "llm" | "embedding" | null;
    provider_model_id?: string | null;
    local_path?: string | null;
    source_id?: string | null;
    availability?: string | null;
  } | null;
  config: Record<string, unknown>;
};

export type PlatformDeploymentProfile = {
  id: string;
  slug: string;
  display_name: string;
  description: string;
  is_active: boolean;
  bindings: PlatformDeploymentBinding[];
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
    models_reachable?: boolean;
    models_status_code?: number;
    embeddings_reachable?: boolean;
    embeddings_status_code?: number;
    embedding_dimension?: number;
    binding_error?: string;
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
    served_model_id?: string | null;
    config?: Record<string, unknown>;
  }>;
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

export async function validatePlatformProvider(providerId: string, token: string): Promise<PlatformProviderValidation> {
  return requestJson<PlatformProviderValidation>(`/v1/platform/providers/${encodeURIComponent(providerId)}/validate`, {
    method: "POST",
    token,
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
