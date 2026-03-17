import { ApiError } from "../auth/authApi";

const backendBaseUrl = (import.meta.env.VITE_BACKEND_BASE_URL as string | undefined)?.trim() || "/api";

type RequestOptions = {
  method?: "GET" | "POST";
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

export type PlatformProviderValidation = {
  provider: Pick<PlatformProvider, "id" | "slug">;
  validation: {
    health: {
      reachable: boolean;
      status_code: number;
    };
    models_reachable?: boolean;
    models_status_code?: number;
  };
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

export async function listPlatformDeployments(token: string): Promise<PlatformDeploymentProfile[]> {
  const result = await requestJson<{ deployments: PlatformDeploymentProfile[] }>("/v1/platform/deployments", { token });
  return result.deployments;
}

export async function validatePlatformProvider(providerId: string, token: string): Promise<PlatformProviderValidation> {
  return requestJson<PlatformProviderValidation>(`/v1/platform/providers/${encodeURIComponent(providerId)}/validate`, {
    method: "POST",
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
