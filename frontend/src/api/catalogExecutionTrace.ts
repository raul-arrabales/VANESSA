export type CatalogExecutionTraceLevel = "info" | "warning" | "error" | string;

export type CatalogExecutionTraceEntry = {
  stage: string;
  level: CatalogExecutionTraceLevel;
  message: string;
  details?: Record<string, unknown>;
};
