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
  task_key?: string | null;
  category?: "predictive" | "generative" | null;
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

export type LocalModelArtifact = {
  artifact_id: string;
  artifact_type: string;
  name?: string | null;
  source_id?: string | null;
  storage_path?: string | null;
  artifact_status?: string | null;
  provenance?: string | null;
  checksum?: string | null;
  linked_model_id?: string | null;
  suggested_model_id?: string | null;
  task_key?: string | null;
  category?: "predictive" | "generative" | null;
  provider?: string | null;
  lifecycle_state?: string | null;
  ready_for_registration: boolean;
  validation_hint?: string | null;
  runtime_requirements?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
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
  global_model_id?: string | null;
  node_id?: string | null;
  name: string;
  provider: string;
  provider_model_id?: string | null;
  backend: "local" | "external_api";
  hosting?: "local" | "cloud";
  owner_type?: "platform" | "user";
  owner_user_id?: number | null;
  source: string;
  availability: "online_only" | "offline_ready";
  runtime_mode_policy?: "online_only" | "online_offline";
  visibility_scope?: "private" | "user" | "group" | "platform";
  model_size_billion?: number | null;
  task_key?: string | null;
  category?: "predictive" | "generative" | null;
  lifecycle_state?: "created" | "registered" | "validated" | "active" | "inactive" | "unregistered" | "deleted" | null;
  is_validation_current?: boolean;
  last_validation_status?: "success" | "failure" | null;
  last_validated_at?: string | null;
  artifact?: {
    storage_path?: string | null;
    artifact_status?: string | null;
    checksum?: string | null;
    provenance?: string | null;
  };
  usage_summary?: {
    total_requests?: number;
    metrics?: Record<string, { value: number; requests: number }>;
  };
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
  const result = await requestJson<{ models: ModelCatalogItem[] }>("/v1/modelops/catalog", { token });
  return result.models;
}

export async function createModelCatalogItem(
  payload: Omit<ModelCatalogItem, "id"> & { id?: string; task_key: string; category?: "predictive" | "generative" },
  token: string,
): Promise<ModelCatalogItem> {
  const result = await requestJson<{ model: ModelCatalogItem }>("/v1/modelops/catalog", {
    method: "POST",
    token,
    body: payload,
  });

  return result.model;
}

export async function discoverHfModels(
  token: string,
  options: { query?: string; task?: string; task_key?: string; sort?: string; limit?: number } = {},
): Promise<HfDiscoveredModel[]> {
  const params = new URLSearchParams();
  if (options.query) params.set("query", options.query);
  if (options.task) params.set("task", options.task);
  if (options.task_key) params.set("task_key", options.task_key);
  if (options.sort) params.set("sort", options.sort);
  if (options.limit) params.set("limit", String(options.limit));
  const query = params.toString();
  const result = await requestJson<{ models: HfDiscoveredModel[] }>(`/v1/modelops/discovery/huggingface${query ? `?${query}` : ""}`, { token });
  return result.models;
}

export async function getHfModelDetails(sourceId: string, token: string): Promise<HfModelDetails> {
  const encoded = encodeURIComponent(sourceId);
  const result = await requestJson<{ model: HfModelDetails }>(`/v1/modelops/discovery/huggingface/${encoded}`, { token });
  return result.model;
}

export async function startModelDownload(
  payload: { source_id: string; name?: string; task_key: string; category?: "predictive" | "generative"; allow_patterns?: string[]; ignore_patterns?: string[] },
  token: string,
): Promise<ModelDownloadJob> {
  const result = await requestJson<{ job: ModelDownloadJob }>("/v1/modelops/downloads", {
    method: "POST",
    token,
    body: payload,
  });
  return result.job;
}

export async function getDownloadJob(jobId: string, token: string): Promise<ModelDownloadJob> {
  const result = await requestJson<{ job: ModelDownloadJob }>(`/v1/modelops/downloads/${encodeURIComponent(jobId)}`, { token });
  return result.job;
}

export async function listDownloadJobs(token: string, status?: string): Promise<ModelDownloadJob[]> {
  const suffix = status ? `?status=${encodeURIComponent(status)}` : "";
  const result = await requestJson<{ jobs: ModelDownloadJob[] }>(`/v1/modelops/downloads${suffix}`, { token });
  return result.jobs;
}

export async function listLocalModelArtifacts(token: string): Promise<LocalModelArtifact[]> {
  const result = await requestJson<{ artifacts: LocalModelArtifact[] }>("/v1/modelops/local-artifacts", { token });
  return result.artifacts;
}

export async function listModelAssignments(token: string): Promise<ModelScopeAssignment[]> {
  try {
    const result = await requestJson<{ assignments: ModelScopeAssignment[] }>("/v1/modelops/sharing", { token });
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
  const result = await requestJson<{ assignment: ModelScopeAssignment }>("/v1/modelops/sharing", {
    method: "PUT",
    token,
    body: { scope, model_ids: modelIds },
  });

  return result.assignment;
}

export async function listEnabledModels(token: string): Promise<ModelCatalogItem[]> {
  const result = await requestJson<{ models: ManagedModel[] }>("/v1/modelops/models?eligible=true&capability=llm_inference", { token });
  return result.models.map((model) => ({
    id: model.id,
    name: model.name,
    provider: model.provider,
    description: typeof model.metadata?.description === "string" ? model.metadata.description : null,
    task_key: model.task_key,
    category: model.category,
  }));
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
  const result = await requestJson<{ credentials: ModelCredential[] }>("/v1/modelops/credentials", { token });
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
  const result = await requestJson<{ credential: ModelCredential }>("/v1/modelops/credentials", {
    method: "POST",
    token,
    body: payload,
  });
  return result.credential;
}

export async function revokeModelCredential(credentialId: string, token: string): Promise<ModelCredential> {
  const result = await requestJson<{ credential: ModelCredential }>(`/v1/modelops/credentials/${encodeURIComponent(credentialId)}`, {
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
    owner_type?: "platform" | "user";
    source?: string;
    availability?: "online_only" | "offline_ready";
    visibility_scope?: "private" | "user" | "group" | "platform";
    provider_model_id?: string;
    credential_id?: string;
    source_id?: string;
    local_path?: string;
    model_size_billion?: number;
    task_key: string;
    category?: "predictive" | "generative";
    comment?: string;
    metadata?: Record<string, unknown>;
  },
  token: string,
): Promise<ManagedModel> {
  const result = await requestJson<{ model: ManagedModel }>("/v1/modelops/models", {
    method: "POST",
    token,
    body: payload,
  });
  return result.model;
}

export async function listAvailableManagedModels(token: string): Promise<ManagedModel[]> {
  return listModelOpsModels(token, { eligible: true });
}

export async function listModelOpsModels(
  token: string,
  options: { eligible?: boolean; capability?: string } = {},
): Promise<ManagedModel[]> {
  const params = new URLSearchParams();
  if (options.eligible) {
    params.set("eligible", "true");
  }
  if (options.capability) {
    params.set("capability", options.capability);
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const result = await requestJson<{ models: ManagedModel[] }>(`/v1/modelops/models${suffix}`, { token });
  return result.models;
}

export async function getManagedModel(modelId: string, token: string): Promise<ManagedModel> {
  const result = await requestJson<{ model: ManagedModel }>(`/v1/modelops/models/${encodeURIComponent(modelId)}`, { token });
  return result.model;
}

export async function getManagedModelUsage(
  modelId: string,
  token: string,
): Promise<{ model_id: string; usage: ManagedModel["usage_summary"] }> {
  return requestJson<{ model_id: string; usage: ManagedModel["usage_summary"] }>(
    `/v1/modelops/models/${encodeURIComponent(modelId)}/usage`,
    { token },
  );
}

export async function getManagedModelValidations(
  modelId: string,
  token: string,
  limit = 20,
): Promise<{
  model_id: string;
  validations: Array<Record<string, unknown>>;
}> {
  return requestJson<{
    model_id: string;
    validations: Array<Record<string, unknown>>;
  }>(`/v1/modelops/models/${encodeURIComponent(modelId)}/validations?limit=${encodeURIComponent(String(limit))}`, { token });
}

export async function registerExistingManagedModel(modelId: string, token: string): Promise<ManagedModel> {
  const result = await requestJson<{ model: ManagedModel }>(`/v1/modelops/models/${encodeURIComponent(modelId)}/register`, {
    method: "POST",
    token,
  });
  return result.model;
}

export async function validateManagedModel(modelId: string, token: string): Promise<ManagedModel> {
  const result = await requestJson<{ model: ManagedModel }>(`/v1/modelops/models/${encodeURIComponent(modelId)}/validate`, {
    method: "POST",
    token,
  });
  return result.model;
}

export async function activateManagedModel(modelId: string, token: string): Promise<ManagedModel> {
  const result = await requestJson<{ model: ManagedModel }>(`/v1/modelops/models/${encodeURIComponent(modelId)}/activate`, {
    method: "POST",
    token,
  });
  return result.model;
}

export async function deactivateManagedModel(modelId: string, token: string): Promise<ManagedModel> {
  const result = await requestJson<{ model: ManagedModel }>(`/v1/modelops/models/${encodeURIComponent(modelId)}/deactivate`, {
    method: "POST",
    token,
  });
  return result.model;
}

export async function unregisterManagedModel(modelId: string, token: string): Promise<ManagedModel> {
  const result = await requestJson<{ model: ManagedModel }>(`/v1/modelops/models/${encodeURIComponent(modelId)}/unregister`, {
    method: "POST",
    token,
  });
  return result.model;
}

export async function deleteManagedModel(modelId: string, token: string): Promise<void> {
  await requestJson<{ deleted: boolean }>(`/v1/modelops/models/${encodeURIComponent(modelId)}`, {
    method: "DELETE",
    token,
  });
}
