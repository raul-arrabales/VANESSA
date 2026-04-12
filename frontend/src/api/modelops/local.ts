import { requestJson } from "./request";
import type {
  HfDiscoveredModel,
  HfModelDetails,
  LocalModelArtifact,
  ModelCatalogItem,
  ModelDownloadJob,
} from "./types";

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
  options: { query?: string; task?: string; task_key?: string; sort?: string; limit?: number; offset?: number } = {},
): Promise<HfDiscoveredModel[]> {
  const params = new URLSearchParams();
  if (options.query) params.set("query", options.query);
  if (options.task) params.set("task", options.task);
  if (options.task_key) params.set("task_key", options.task_key);
  if (options.sort) params.set("sort", options.sort);
  if (options.limit) params.set("limit", String(options.limit));
  if (options.offset) params.set("offset", String(options.offset));
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
