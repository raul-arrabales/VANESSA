export const TASK_OPTIONS = [
  { value: "llm", label: "LLM / Text generation", category: "generative" as const },
  { value: "embeddings", label: "Embeddings", category: "predictive" as const },
  { value: "translation", label: "Translation", category: "generative" as const },
  { value: "classification", label: "Classification", category: "predictive" as const },
] as const;

export const MODEL_ACCESS_SCOPES = ["user", "admin", "superadmin"] as const;

export type TaskOption = (typeof TASK_OPTIONS)[number];
