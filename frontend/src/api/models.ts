import { ApiError } from "../auth/authApi";

const backendBaseUrl = (import.meta.env.VITE_BACKEND_BASE_URL as string | undefined)?.trim() || "/api";

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  token?: string;
};

export type ModelCatalogItem = {
  id: string;
  name: string;
  provider?: string | null;
  source_id?: string | null;
  local_path?: string | null;
  status?: string | null;
  description?: string | null;
  metadata?: Record<string, unknown>;
};

export type ModelScopeAssignment = {
  scope: string;
  model_ids: string[];
};

export type HfDiscoveredModel = {
  source_id: string;
  name: string;
  downloads?: number | null;
  likes?: number | null;
  tags: string[];
  provider: string;
};

export type HfModelDetails = {
  source_id: string;
  name: string;
  sha?: string | null;
  downloads?: number | null;
  likes?: number | null;
  tags: string[];
  files: Array<{ path: string; size?: number | null }>;
};

export type ModelDownloadJob = {
  job_id: string;
  provider: string;
  source_id: string;
  target_dir: string;
  model_id?: string | null;
  status: string;
  error_message?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};



export type ModelCredential = {
  id: string;
  owner_user_id: number;
  credential_scope: "platform" | "personal";
  provider: string;
  display_name: string;
  api_base_url?: string | null;
  api_key_last4: string;
  is_active: boolean;
  revoked_at?: string | null;
};

export type ManagedModel = {
  id: string;
  name: string;
  provider: string;
  provider_model_id?: string | null;
  origin: "platform" | "personal";
  backend: "local" | "external_api";
  source: string;
  availability: "online_only" | "offline_ready";
  access_scope: "private" | "assigned" | "global";
  credential_owner: "platform" | "you";
  model_size_billion?: number | null;
  model_type?: string | null;
  comment?: string | null;
  metadata?: Record<string, unknown>;
};

export type InferenceResult = {
  output: string;
  response?: Record<string, unknown>;
};

export type ChatHistoryItem = {
  role: "system" | "user" | "assistant" | "tool";
  content: string;
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

export async function listModelCatalog(token: string): Promise<ModelCatalogItem[]> {
  const result = await requestJson<{ models: ModelCatalogItem[] }>("/v1/models/catalog", { token });
  return result.models;
}

export async function createModelCatalogItem(
  payload: Omit<ModelCatalogItem, "id"> & { id?: string },
  token: string,
): Promise<ModelCatalogItem> {
  const result = await requestJson<{ model: ModelCatalogItem }>("/v1/models/catalog", {
    method: "POST",
    token,
    body: payload,
  });

  return result.model;
}

export async function discoverHfModels(
  token: string,
  options: { query?: string; task?: string; sort?: string; limit?: number } = {},
): Promise<HfDiscoveredModel[]> {
  const params = new URLSearchParams();
  if (options.query) params.set("query", options.query);
  if (options.task) params.set("task", options.task);
  if (options.sort) params.set("sort", options.sort);
  if (options.limit) params.set("limit", String(options.limit));
  const query = params.toString();
  const result = await requestJson<{ models: HfDiscoveredModel[] }>(`/v1/models/discovery/huggingface${query ? `?${query}` : ""}`, { token });
  return result.models;
}

export async function getHfModelDetails(sourceId: string, token: string): Promise<HfModelDetails> {
  const encoded = encodeURIComponent(sourceId);
  const result = await requestJson<{ model: HfModelDetails }>(`/v1/models/discovery/huggingface/${encoded}`, { token });
  return result.model;
}

export async function startModelDownload(
  payload: { source_id: string; name?: string; allow_patterns?: string[]; ignore_patterns?: string[] },
  token: string,
): Promise<ModelDownloadJob> {
  const result = await requestJson<{ job: ModelDownloadJob }>("/v1/models/downloads", {
    method: "POST",
    token,
    body: payload,
  });
  return result.job;
}

export async function getDownloadJob(jobId: string, token: string): Promise<ModelDownloadJob> {
  const result = await requestJson<{ job: ModelDownloadJob }>(`/v1/models/downloads/${encodeURIComponent(jobId)}`, { token });
  return result.job;
}

export async function listDownloadJobs(token: string, status?: string): Promise<ModelDownloadJob[]> {
  const suffix = status ? `?status=${encodeURIComponent(status)}` : "";
  const result = await requestJson<{ jobs: ModelDownloadJob[] }>(`/v1/models/downloads${suffix}`, { token });
  return result.jobs;
}

export async function listModelAssignments(token: string): Promise<ModelScopeAssignment[]> {
  try {
    const result = await requestJson<{ assignments: ModelScopeAssignment[] }>("/v1/model-governance/assignments", { token });
    return result.assignments;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return [];
    }
    throw error;
  }
}

export async function updateModelAssignment(
  scope: string,
  modelIds: string[],
  token: string,
): Promise<ModelScopeAssignment> {
  const result = await requestJson<{ assignment: ModelScopeAssignment }>("/v1/model-governance/assignments", {
    method: "PUT",
    token,
    body: { scope, model_ids: modelIds },
  });

  return result.assignment;
}

export async function listEnabledModels(token: string): Promise<ModelCatalogItem[]> {
  const result = await requestJson<{
    models: Array<{
      id?: string;
      name?: string;
      provider?: string | null;
      description?: string | null;
      model_id?: string;
      metadata?: { name?: string; description?: string };
    }>;
  }>("/v1/model-governance/enabled", { token });

  return result.models.map((model) => {
    const fallbackId = model.model_id ?? "";
    const id = model.id ?? fallbackId;
    const metadata = model.metadata ?? {};
    return {
      id,
      name: model.name ?? metadata.name ?? id,
      provider: model.provider,
      description: model.description ?? metadata.description ?? null,
    };
  }).filter((model) => model.id);
}

export async function runInference(
  prompt: string,
  model: string,
  token: string,
  history: ChatHistoryItem[] = [],
): Promise<InferenceResult> {
  return requestJson<InferenceResult>("/v1/models/inference", {
    method: "POST",
    token,
    body: { prompt, model, history },
  });
}


export async function listModelCredentials(token: string): Promise<ModelCredential[]> {
  const result = await requestJson<{ credentials: ModelCredential[] }>("/v1/models/credentials", { token });
  return result.credentials;
}

export async function createModelCredential(
  payload: {
    provider: string;
    display_name?: string;
    api_base_url?: string;
    api_key: string;
    credential_scope?: "platform" | "personal";
    owner_user_id?: number;
  },
  token: string,
): Promise<ModelCredential> {
  const result = await requestJson<{ credential: ModelCredential }>("/v1/models/credentials", {
    method: "POST",
    token,
    body: payload,
  });
  return result.credential;
}

export async function revokeModelCredential(credentialId: string, token: string): Promise<ModelCredential> {
  const result = await requestJson<{ credential: ModelCredential }>(`/v1/models/credentials/${encodeURIComponent(credentialId)}`, {
    method: "DELETE",
    token,
  });
  return result.credential;
}

export async function registerManagedModel(
  payload: {
    id: string;
    name: string;
    provider: string;
    backend: "local" | "external_api";
    origin: "platform" | "personal";
    source?: string;
    availability?: "online_only" | "offline_ready";
    access_scope?: "private" | "assigned" | "global";
    provider_model_id?: string;
    credential_id?: string;
    source_id?: string;
    local_path?: string;
    model_size_billion?: number;
    model_type?: string;
    comment?: string;
    metadata?: Record<string, unknown>;
  },
  token: string,
): Promise<ManagedModel> {
  const result = await requestJson<{ model: ManagedModel }>("/v1/models/register", {
    method: "POST",
    token,
    body: payload,
  });
  return result.model;
}

export async function listAvailableManagedModels(token: string): Promise<ManagedModel[]> {
  const result = await requestJson<{ models: ManagedModel[] }>("/v1/models/available", { token });
  return result.models;
}
