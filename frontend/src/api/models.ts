import { ApiError } from "../auth/authApi";

const backendBaseUrl = (import.meta.env.VITE_BACKEND_BASE_URL as string | undefined)?.trim() || "/api";

type RequestOptions = {
  method?: "GET" | "POST" | "PUT";
  body?: unknown;
  token?: string;
};

export type ModelCatalogItem = {
  id: string;
  name: string;
  provider?: string | null;
  description?: string | null;
};

export type ModelScopeAssignment = {
  scope: string;
  model_ids: string[];
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
  try {
    const result = await requestJson<{ models: ModelCatalogItem[] }>("/models/catalog", { token });
    return result.models;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return listEnabledModels(token);
    }
    throw error;
  }
}

export async function createModelCatalogItem(
  payload: Omit<ModelCatalogItem, "id"> & { id?: string },
  token: string,
): Promise<ModelCatalogItem> {
  const result = await requestJson<{ model: ModelCatalogItem }>("/models/catalog", {
    method: "POST",
    token,
    body: payload,
  });

  return result.model;
}

export async function listModelAssignments(token: string): Promise<ModelScopeAssignment[]> {
  try {
    const result = await requestJson<{ assignments: ModelScopeAssignment[] }>("/models/assignments", { token });
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
  const result = await requestJson<{ assignment: ModelScopeAssignment }>("/models/assignments", {
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
  }>("/models/enabled", { token });

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
  return requestJson<InferenceResult>("/inference", {
    method: "POST",
    token,
    body: { prompt, model, history },
  });
}
