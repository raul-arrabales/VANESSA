import { ApiError } from "../auth/authApi";
import { requestJson } from "./modelops/request";

const backendBaseUrl = (import.meta.env.VITE_BACKEND_BASE_URL as string | undefined)?.trim() || "/api";

export type KnowledgeBase = {
  id: string;
  slug: string;
  display_name: string;
  description: string;
  index_name: string;
  backing_provider_key: string;
  lifecycle_state: "active" | "archived" | string;
  sync_status: "ready" | "syncing" | "error" | string;
  schema: Record<string, unknown>;
  document_count: number;
  eligible_for_binding: boolean;
  last_sync_at?: string | null;
  last_sync_error?: string | null;
  last_sync_summary?: string | null;
  binding_count?: number;
  created_at?: string | null;
  updated_at?: string | null;
  deployment_usage?: Array<{
    deployment_profile: {
      id: string;
      slug: string;
      display_name: string;
    };
    capability: string;
  }>;
};

export type KnowledgeBaseQueryResult = {
  id: string;
  title: string;
  snippet: string;
  uri?: string | null;
  source_type?: string | null;
  metadata: Record<string, unknown>;
  score?: number | null;
  score_kind?: string | null;
};

export type KnowledgeBaseQueryResponse = {
  knowledge_base_id: string;
  retrieval: {
    index: string;
    result_count: number;
    top_k: number;
  };
  results: KnowledgeBaseQueryResult[];
};

export type KnowledgeDocument = {
  id: string;
  knowledge_base_id: string;
  title: string;
  source_type: string;
  source_name?: string | null;
  uri?: string | null;
  text: string;
  metadata: Record<string, unknown>;
  chunk_count: number;
  source_id?: string | null;
  source_path?: string | null;
  source_document_key?: string | null;
  managed_by_source?: boolean;
  created_at?: string | null;
  updated_at?: string | null;
};

export type KnowledgeSource = {
  id: string;
  knowledge_base_id: string;
  source_type: string;
  display_name: string;
  relative_path: string;
  include_globs: string[];
  exclude_globs: string[];
  lifecycle_state: "active" | "archived" | string;
  last_sync_status: "idle" | "syncing" | "ready" | "error" | string;
  last_sync_at?: string | null;
  last_sync_error?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type KnowledgeSyncRun = {
  id: string;
  knowledge_base_id: string;
  source_id?: string | null;
  source_display_name?: string | null;
  status: "syncing" | "ready" | "error" | string;
  scanned_file_count: number;
  changed_file_count: number;
  deleted_file_count: number;
  created_document_count: number;
  updated_document_count: number;
  deleted_document_count: number;
  error_summary?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
};

function buildUrl(path: string): string {
  return `${backendBaseUrl.replace(/\/$/, "")}${path}`;
}

export async function listKnowledgeBases(
  token: string,
  options: { eligible?: boolean; backingProviderKey?: string } = {},
): Promise<KnowledgeBase[]> {
  const params = new URLSearchParams();
  if (options.eligible) {
    params.set("eligible", "true");
  }
  if (options.backingProviderKey) {
    params.set("backing_provider_key", options.backingProviderKey);
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const result = await requestJson<{ knowledge_bases: KnowledgeBase[] }>(`/v1/context/knowledge-bases${suffix}`, { token });
  return result.knowledge_bases;
}

export async function createKnowledgeBase(
  payload: {
    slug: string;
    display_name: string;
    description: string;
    backing_provider_key?: string;
    lifecycle_state?: string;
    schema?: Record<string, unknown>;
  },
  token: string,
): Promise<KnowledgeBase> {
  const result = await requestJson<{ knowledge_base: KnowledgeBase }>("/v1/context/knowledge-bases", {
    method: "POST",
    token,
    body: payload,
  });
  return result.knowledge_base;
}

export async function getKnowledgeBase(knowledgeBaseId: string, token: string): Promise<KnowledgeBase> {
  const result = await requestJson<{ knowledge_base: KnowledgeBase }>(
    `/v1/context/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}`,
    { token },
  );
  return result.knowledge_base;
}

export async function updateKnowledgeBase(
  knowledgeBaseId: string,
  payload: {
    slug: string;
    display_name: string;
    description: string;
    lifecycle_state: string;
  },
  token: string,
): Promise<KnowledgeBase> {
  const result = await requestJson<{ knowledge_base: KnowledgeBase }>(
    `/v1/context/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}`,
    {
      method: "PUT",
      token,
      body: payload,
    },
  );
  return result.knowledge_base;
}

export async function deleteKnowledgeBase(knowledgeBaseId: string, token: string): Promise<void> {
  await requestJson<{ deleted: boolean }>(`/v1/context/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}`, {
    method: "DELETE",
    token,
  });
}

export async function resyncKnowledgeBase(knowledgeBaseId: string, token: string): Promise<KnowledgeBase> {
  const result = await requestJson<{ knowledge_base: KnowledgeBase }>(
    `/v1/context/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/resync`,
    {
      method: "POST",
      token,
    },
  );
  return result.knowledge_base;
}

export async function queryKnowledgeBase(
  knowledgeBaseId: string,
  payload: {
    query_text: string;
    top_k?: number;
  },
  token: string,
): Promise<KnowledgeBaseQueryResponse> {
  return requestJson<KnowledgeBaseQueryResponse>(
    `/v1/context/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/query`,
    {
      method: "POST",
      token,
      body: payload,
    },
  );
}

export async function listKnowledgeBaseDocuments(knowledgeBaseId: string, token: string): Promise<KnowledgeDocument[]> {
  const result = await requestJson<{ documents: KnowledgeDocument[] }>(
    `/v1/context/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/documents`,
    { token },
  );
  return result.documents;
}

export async function listKnowledgeSources(knowledgeBaseId: string, token: string): Promise<KnowledgeSource[]> {
  const result = await requestJson<{ sources: KnowledgeSource[] }>(
    `/v1/context/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/sources`,
    { token },
  );
  return result.sources;
}

export async function createKnowledgeSource(
  knowledgeBaseId: string,
  payload: {
    display_name: string;
    relative_path: string;
    include_globs?: string[];
    exclude_globs?: string[];
    lifecycle_state?: string;
    source_type?: string;
  },
  token: string,
): Promise<KnowledgeSource> {
  const result = await requestJson<{ source: KnowledgeSource }>(
    `/v1/context/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/sources`,
    {
      method: "POST",
      token,
      body: payload,
    },
  );
  return result.source;
}

export async function updateKnowledgeSource(
  knowledgeBaseId: string,
  sourceId: string,
  payload: {
    display_name: string;
    relative_path: string;
    include_globs?: string[];
    exclude_globs?: string[];
    lifecycle_state?: string;
    source_type?: string;
  },
  token: string,
): Promise<KnowledgeSource> {
  const result = await requestJson<{ source: KnowledgeSource }>(
    `/v1/context/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/sources/${encodeURIComponent(sourceId)}`,
    {
      method: "PUT",
      token,
      body: payload,
    },
  );
  return result.source;
}

export async function deleteKnowledgeSource(
  knowledgeBaseId: string,
  sourceId: string,
  token: string,
): Promise<void> {
  await requestJson<{ deleted: boolean }>(
    `/v1/context/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/sources/${encodeURIComponent(sourceId)}`,
    {
      method: "DELETE",
      token,
    },
  );
}

export async function syncKnowledgeSource(
  knowledgeBaseId: string,
  sourceId: string,
  token: string,
): Promise<{ knowledge_base: KnowledgeBase; source: KnowledgeSource; sync_run: KnowledgeSyncRun }> {
  return requestJson<{ knowledge_base: KnowledgeBase; source: KnowledgeSource; sync_run: KnowledgeSyncRun }>(
    `/v1/context/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/sources/${encodeURIComponent(sourceId)}/sync`,
    {
      method: "POST",
      token,
    },
  );
}

export async function listKnowledgeSyncRuns(knowledgeBaseId: string, token: string): Promise<KnowledgeSyncRun[]> {
  const result = await requestJson<{ sync_runs: KnowledgeSyncRun[] }>(
    `/v1/context/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/sync-runs`,
    { token },
  );
  return result.sync_runs;
}

export async function createKnowledgeBaseDocument(
  knowledgeBaseId: string,
  payload: {
    title: string;
    source_type?: string;
    source_name?: string | null;
    uri?: string | null;
    text: string;
    metadata?: Record<string, unknown>;
  },
  token: string,
): Promise<KnowledgeDocument> {
  const result = await requestJson<{ document: KnowledgeDocument }>(
    `/v1/context/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/documents`,
    {
      method: "POST",
      token,
      body: payload,
    },
  );
  return result.document;
}

export async function updateKnowledgeBaseDocument(
  knowledgeBaseId: string,
  documentId: string,
  payload: {
    title: string;
    source_type?: string;
    source_name?: string | null;
    uri?: string | null;
    text: string;
    metadata?: Record<string, unknown>;
  },
  token: string,
): Promise<KnowledgeDocument> {
  const result = await requestJson<{ document: KnowledgeDocument }>(
    `/v1/context/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/documents/${encodeURIComponent(documentId)}`,
    {
      method: "PUT",
      token,
      body: payload,
    },
  );
  return result.document;
}

export async function deleteKnowledgeBaseDocument(
  knowledgeBaseId: string,
  documentId: string,
  token: string,
): Promise<void> {
  await requestJson<{ deleted: boolean }>(
    `/v1/context/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/documents/${encodeURIComponent(documentId)}`,
    {
      method: "DELETE",
      token,
    },
  );
}

export async function uploadKnowledgeBaseDocuments(
  knowledgeBaseId: string,
  files: File[],
  token: string,
): Promise<{ documents: KnowledgeDocument[]; count: number }> {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file);
  });
  const response = await fetch(buildUrl(`/v1/context/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/uploads`), {
    method: "POST",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: formData,
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
      throw new ApiError("Backend returned a non-JSON response", response.status, "invalid_response_format");
    }
  }
  if (!response.ok) {
    const message = String(payload.message ?? payload.error ?? `HTTP ${response.status}`);
    const code = payload.error ? String(payload.error) : undefined;
    throw new ApiError(message, response.status, code);
  }
  return payload as unknown as { documents: KnowledgeDocument[]; count: number };
}
