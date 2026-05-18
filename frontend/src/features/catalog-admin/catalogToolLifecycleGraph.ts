import type { TFunction } from "i18next";
import type { LifecycleGraphDefinition, LifecycleTransitionDefinition } from "../../components/LifecycleGraph";
import type { CatalogTool } from "../../api/catalog";
import { catalogToolBackendLabelKey } from "./catalogToolBackends";

export const CATALOG_TOOL_LIFECYCLE_STATE_IDS = [
  "draft",
  "published_unvalidated",
  "validation_failed",
  "validation_stale",
  "ready",
] as const;

export type CatalogToolLifecycleState = typeof CATALOG_TOOL_LIFECYCLE_STATE_IDS[number];

export const CATALOG_TOOL_LIFECYCLE_TRANSITIONS: LifecycleTransitionDefinition[] = [
  { from: "draft", to: "published_unvalidated" },
  { from: "published_unvalidated", to: "ready" },
  { from: "published_unvalidated", to: "validation_failed" },
  { from: "validation_failed", to: "published_unvalidated" },
  { from: "validation_failed", to: "ready" },
  { from: "ready", to: "validation_stale" },
  { from: "validation_stale", to: "ready" },
  { from: "validation_stale", to: "validation_failed" },
  { from: "published_unvalidated", to: "draft" },
  { from: "validation_failed", to: "draft" },
  { from: "validation_stale", to: "draft" },
  { from: "ready", to: "draft" },
];

export function createCatalogToolLifecycleGraphDefinition(t: TFunction<"common">): LifecycleGraphDefinition {
  return {
    artifactType: "catalog-tool",
    states: CATALOG_TOOL_LIFECYCLE_STATE_IDS.map((stateId, index) => ({
      id: stateId,
      label: t(`catalogControl.tools.lifecycle.states.${stateId}`),
      x: [90, 270, 450, 630, 450][index],
      y: [80, 80, 80, 80, 210][index],
    })),
    transitions: CATALOG_TOOL_LIFECYCLE_TRANSITIONS.map((transition) => ({
      ...transition,
      label: t(`catalogControl.tools.lifecycle.transitions.${transition.from}.${transition.to}`),
    })),
  };
}

export function getCatalogToolLifecycleState(tool: CatalogTool): CatalogToolLifecycleState {
  if (!tool.published) {
    return "draft";
  }

  const validationStatus = tool.validation_status;
  const lastValidationStatus = String(validationStatus?.last_validation_status || "").trim().toLowerCase();
  if (lastValidationStatus === "success" && validationStatus?.is_validation_current === true) {
    return "ready";
  }
  if (lastValidationStatus === "success") {
    return "validation_stale";
  }
  if (lastValidationStatus === "failed" || lastValidationStatus === "failure") {
    return "validation_failed";
  }
  return "published_unvalidated";
}

export function getCatalogToolLifecycleSummary(t: TFunction<"common">, tool: CatalogTool): string {
  const backend = t(`catalogControl.executionBackend.${catalogToolBackendLabelKey(tool.spec.execution_backend)}`);
  const publishStatus = tool.published ? t("catalogControl.badges.published") : t("catalogControl.badges.draft");
  const validationStatus = String(tool.validation_status?.last_validation_status || "unknown").toLowerCase();
  const validationLabel = t(`catalogControl.tools.lifecycle.validation.${validationStatus}`, {
    defaultValue: validationStatus,
  });
  const compatibility = tool.spec.offline_compatible
    ? t("catalogControl.tools.offlineCompatible")
    : t("catalogControl.tools.networkRequired");

  return t("catalogControl.tools.lifecycle.summary", {
    backend,
    publishStatus,
    validationStatus: validationLabel,
    compatibility,
  });
}
