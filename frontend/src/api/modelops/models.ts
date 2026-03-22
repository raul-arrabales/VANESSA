import { requestJson } from "./request";
import type {
  ChatHistoryItem,
  InferenceResult,
  ManagedModel,
  ModelCatalogItem,
  ModelValidationRecord,
  ModelUsageSummary,
} from "./types";

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
): Promise<{ model_id: string; usage: ModelUsageSummary }> {
  return requestJson<{ model_id: string; usage: ModelUsageSummary }>(
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
  validations: ModelValidationRecord[];
}> {
  return requestJson<{
    model_id: string;
    validations: ModelValidationRecord[];
  }>(`/v1/modelops/models/${encodeURIComponent(modelId)}/validations?limit=${encodeURIComponent(String(limit))}`, { token });
}

export async function registerExistingManagedModel(modelId: string, token: string): Promise<ManagedModel> {
  const result = await requestJson<{ model: ManagedModel }>(`/v1/modelops/models/${encodeURIComponent(modelId)}/register`, {
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
