export type ManagedModelLifecycleState =
  | "created"
  | "registered"
  | "validated"
  | "active"
  | "inactive"
  | "unregistered"
  | "deleted";

export type ManagedModelTaskKey =
  | "llm"
  | "embeddings"
  | "translation"
  | "classification"
  | string;

export type ModelUsageMetric = {
  value: number;
  requests: number;
};

export type ModelUsageSummary = {
  total_requests: number;
  metrics: Record<string, ModelUsageMetric>;
};

export type ModelValidationRecord = {
  id: string;
  model_id: string;
  validator_kind?: string | null;
  trigger_reason?: string | null;
  result: "success" | "failure" | string;
  summary: string;
  error_details: Record<string, unknown>;
  config_fingerprint?: string | null;
  validated_by_user_id?: number | null;
  created_at?: string | null;
};

export type ModelCatalogItem = {
  id: string;
  name: string;
  provider?: string | null;
  source_id?: string | null;
  local_path?: string | null;
  status?: string | null;
  task_key?: ManagedModelTaskKey | null;
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

export type HfModelFileDetails = {
  path: string;
  size?: number | null;
  file_type?: string | null;
  blob_id?: string | null;
  lfs?: Record<string, unknown> | null;
};

export type HfModelDetails = {
  source_id: string;
  name: string;
  sha?: string | null;
  downloads?: number | null;
  likes?: number | null;
  tags: string[];
  author?: string | null;
  pipeline_tag?: string | null;
  library_name?: string | null;
  gated?: string | boolean | null;
  private?: boolean | null;
  disabled?: boolean | null;
  created_at?: string | null;
  last_modified?: string | null;
  used_storage?: number | null;
  card_data?: Record<string, unknown> | null;
  config?: Record<string, unknown> | null;
  safetensors?: Record<string, unknown> | null;
  model_index?: unknown | null;
  transformers_info?: Record<string, unknown> | null;
  files: HfModelFileDetails[];
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
  task_key?: ManagedModelTaskKey | null;
  category?: "predictive" | "generative" | null;
  provider?: string | null;
  lifecycle_state?: ManagedModelLifecycleState | null;
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

export type ModelArtifactSummary = {
  storage_path?: string | null;
  artifact_status?: string | null;
  checksum?: string | null;
  provenance?: string | null;
};

export type ManagedModel = {
  id: string;
  global_model_id?: string | null;
  node_id?: string | null;
  name: string;
  provider: string;
  provider_model_id?: string | null;
  source_id?: string | null;
  backend: "local" | "external_api";
  hosting?: "local" | "cloud";
  owner_type?: "platform" | "user";
  owner_user_id?: number | null;
  source: string;
  availability: "online_only" | "offline_ready";
  runtime_mode_policy?: "online_only" | "online_offline";
  visibility_scope?: "private" | "user" | "group" | "platform";
  model_size_billion?: number | null;
  task_key?: ManagedModelTaskKey | null;
  category?: "predictive" | "generative" | null;
  lifecycle_state?: ManagedModelLifecycleState | null;
  is_validation_current?: boolean;
  last_validation_status?: "success" | "failure" | null;
  last_validated_at?: string | null;
  artifact?: ModelArtifactSummary;
  usage_summary?: ModelUsageSummary;
  validation_history?: ModelValidationRecord[];
  comment?: string | null;
  metadata?: Record<string, unknown>;
};

export type ModelTestRun = {
  id: string;
  model_id: string;
  task_key?: ManagedModelTaskKey | null;
  result: "success" | "failure";
  summary: string;
  input_payload?: Record<string, unknown>;
  output_payload?: Record<string, unknown>;
  error_details?: Record<string, unknown>;
  latency_ms?: number | null;
  config_fingerprint?: string | null;
  tested_by_user_id?: number | null;
  created_at?: string | null;
};

export type ManagedModelTestRuntime = {
  provider_instance_id: string;
  slug: string;
  display_name: string;
  provider_key: string;
  endpoint_url: string;
  adapter_kind: string;
  enabled: boolean;
  is_active: boolean;
  reachable: boolean;
  status_code: number;
  matches_model: boolean;
  matched_model_id?: string | null;
  matched_model_display_name?: string | null;
  match_source?: string | null;
  matched_value?: string | null;
  loaded_managed_model_id?: string | null;
  loaded_managed_model_name?: string | null;
  loaded_runtime_model_id?: string | null;
  loaded_local_path?: string | null;
  loaded_source_id?: string | null;
  load_state?: "empty" | "loading" | "reconciling" | "loaded" | "error" | string;
  load_error?: string | null;
  advertised_model_ids?: string[];
  advertised_models?: Array<{
    id: string;
    display_name: string;
    capabilities: {
      text: boolean;
      image_input: boolean;
      embeddings: boolean;
    };
    metadata?: Record<string, unknown>;
  }>;
  message?: string | null;
};

export type ModelTestResult = {
  kind: "llm" | "embeddings";
  success: boolean;
  response_text?: string;
  dimension?: number;
  latency_ms?: number | null;
  vector_preview?: number[];
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
