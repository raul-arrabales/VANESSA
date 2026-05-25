import type { CatalogExecutionTraceEntry } from "../../api/catalogExecutionTrace";

const PROGRESS_STAGE_ORDER = [
  "request_received",
  "input_validated",
  "runtime_dispatched",
  "runtime_warnings",
  "completed",
  "failed",
];

export function executionTraceEntries(value: unknown): CatalogExecutionTraceEntry[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.flatMap((entry) => {
    if (!entry || typeof entry !== "object" || Array.isArray(entry)) {
      return [];
    }
    const record = entry as Record<string, unknown>;
    const stage = typeof record.stage === "string" ? record.stage.trim() : "";
    const level = typeof record.level === "string" ? record.level.trim() : "info";
    const message = typeof record.message === "string" ? record.message.trim() : "";
    const details = record.details && typeof record.details === "object" && !Array.isArray(record.details)
      ? record.details as Record<string, unknown>
      : undefined;
    if (!stage || !message) {
      return [];
    }
    return [{ stage, level, message, details }];
  });
}

export function progressIndexFromTrace(entries: CatalogExecutionTraceEntry[]): number | null {
  const lastKnownIndex = entries.reduce((current, entry) => {
    const index = PROGRESS_STAGE_ORDER.indexOf(entry.stage);
    return index >= 0 ? Math.max(current, Math.min(index, 3)) : current;
  }, -1);
  return lastKnownIndex >= 0 ? lastKnownIndex : null;
}

export function formatRuntimeDetailValue(value: unknown): string {
  if (typeof value === "boolean") {
    return value ? "yes" : "no";
  }
  if (typeof value === "number") {
    return Number.isFinite(value) ? String(value) : "";
  }
  if (typeof value === "string") {
    return value;
  }
  if (Array.isArray(value)) {
    return value.map(formatRuntimeDetailValue).filter(Boolean).join(", ");
  }
  if (value && typeof value === "object") {
    return JSON.stringify(value);
  }
  return "";
}

export function runtimeDetailRows(details: Record<string, unknown> | undefined): Array<{ key: string; value: string }> {
  if (!details) {
    return [];
  }
  return Object.entries(details).flatMap(([key, value]) => {
    const formatted = formatRuntimeDetailValue(value);
    return formatted ? [{ key, value: formatted }] : [];
  });
}
