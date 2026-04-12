import type { HfModelDetails, HfModelFileDetails } from "../../../api/modelops/types";

export type HfModelDetailMetadataSection = {
  key: string;
  label: string;
  value: unknown;
};

export function formatOptionalValue(value: unknown, emptyLabel: string): string {
  if (value === null || value === undefined || value === "") {
    return emptyLabel;
  }
  if (typeof value === "boolean") {
    return value ? "yes" : "no";
  }
  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : emptyLabel;
  }
  return String(value);
}

export function formatBytes(value: number | null | undefined, emptyLabel: string): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return emptyLabel;
  }
  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits: value >= 1024 * 1024 ? 1 : 0,
    notation: value >= 1024 * 1024 * 1024 ? "compact" : "standard",
  }).format(value);
}

export function jsonBlock(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

export function getFileFormatSummary(files: HfModelFileDetails[]): Array<{ type: string; count: number }> {
  const counts = new Map<string, number>();
  files.forEach((file) => {
    const type = file.file_type || "unknown";
    counts.set(type, (counts.get(type) ?? 0) + 1);
  });
  return [...counts.entries()]
    .map(([type, count]) => ({ type, count }))
    .sort((left, right) => left.type.localeCompare(right.type));
}

export function getMetadataSections(
  model: HfModelDetails,
  labels: {
    cardData: string;
    config: string;
    safetensors: string;
    modelIndex: string;
    transformersInfo: string;
  },
): HfModelDetailMetadataSection[] {
  return [
    { key: "card_data", label: labels.cardData, value: model.card_data },
    { key: "config", label: labels.config, value: model.config },
    { key: "safetensors", label: labels.safetensors, value: model.safetensors },
    { key: "model_index", label: labels.modelIndex, value: model.model_index },
    { key: "transformers_info", label: labels.transformersInfo, value: model.transformers_info },
  ].filter((section) => section.value !== null && section.value !== undefined);
}
