import type { TFunction } from "i18next";
import type { LifecycleGraphDefinition, LifecycleTransitionDefinition } from "../../components/LifecycleGraph";
import type { CatalogMcpServer } from "../../api/catalog";

export const CATALOG_MCP_LIFECYCLE_STATE_IDS = [
  "draft",
  "disabled",
  "enabled_unvalidated",
  "validation_failed",
  "validation_stale",
  "enabled_ready",
] as const;

export type CatalogMcpLifecycleState = typeof CATALOG_MCP_LIFECYCLE_STATE_IDS[number];

export const CATALOG_MCP_LIFECYCLE_TRANSITIONS: LifecycleTransitionDefinition[] = [
  { from: "draft", to: "enabled_unvalidated" },
  { from: "draft", to: "disabled" },
  { from: "disabled", to: "enabled_unvalidated" },
  { from: "enabled_unvalidated", to: "enabled_ready" },
  { from: "enabled_unvalidated", to: "validation_failed" },
  { from: "validation_failed", to: "enabled_unvalidated" },
  { from: "validation_failed", to: "enabled_ready" },
  { from: "enabled_ready", to: "validation_stale" },
  { from: "validation_stale", to: "enabled_ready" },
  { from: "validation_stale", to: "validation_failed" },
  { from: "disabled", to: "draft" },
  { from: "enabled_unvalidated", to: "draft" },
  { from: "validation_failed", to: "draft" },
  { from: "validation_stale", to: "draft" },
  { from: "enabled_ready", to: "draft" },
  { from: "enabled_unvalidated", to: "disabled" },
  { from: "validation_failed", to: "disabled" },
  { from: "validation_stale", to: "disabled" },
  { from: "enabled_ready", to: "disabled" },
];

export function createCatalogMcpLifecycleGraphDefinition(t: TFunction<"common">): LifecycleGraphDefinition {
  return {
    artifactType: "catalog-mcp",
    states: CATALOG_MCP_LIFECYCLE_STATE_IDS.map((stateId, index) => ({
      id: stateId,
      label: t(`catalogControl.mcp.lifecycle.states.${stateId}`),
      x: [90, 250, 410, 570, 250, 570][index],
      y: [80, 80, 80, 80, 210, 210][index],
    })),
    transitions: CATALOG_MCP_LIFECYCLE_TRANSITIONS.map((transition) => ({
      ...transition,
      label: t(`catalogControl.mcp.lifecycle.transitions.${transition.from}.${transition.to}`),
    })),
  };
}

export function getCatalogMcpLifecycleState(server: CatalogMcpServer): CatalogMcpLifecycleState {
  if (!server.published) {
    return "draft";
  }
  if (!server.spec.enabled) {
    return "disabled";
  }

  const validationStatus = server.validation_status;
  const lastValidationStatus = String(validationStatus?.last_validation_status || "").trim().toLowerCase();
  if (lastValidationStatus === "success" && validationStatus?.is_validation_current === true) {
    return "enabled_ready";
  }
  if (lastValidationStatus === "success") {
    return "validation_stale";
  }
  if (lastValidationStatus === "failed" || lastValidationStatus === "failure") {
    return "validation_failed";
  }
  return "enabled_unvalidated";
}

export function getCatalogMcpLifecycleSummary(
  t: TFunction<"common">,
  server: CatalogMcpServer,
  backingToolName: string,
): string {
  const metadata = server.spec.metadata;
  const category = t(`catalogControl.mcp.metadata.category.${metadata.category}`);
  const risk = t(`catalogControl.mcp.metadata.riskLevel.${metadata.risk_level}`);
  const exposureStatus = server.spec.enabled ? t("catalogControl.badges.enabled") : t("catalogControl.badges.disabled");
  const validationStatus = String(server.validation_status?.last_validation_status || "unknown").toLowerCase();
  const validationLabel = t(`catalogControl.mcp.lifecycle.validation.${validationStatus}`, {
    defaultValue: validationStatus,
  });
  const locality = metadata.local ? t("catalogControl.mcp.lifecycle.flags.local") : t("catalogControl.mcp.lifecycle.flags.network");
  const statefulness = metadata.stateless ? t("catalogControl.mcp.lifecycle.flags.stateless") : t("catalogControl.mcp.lifecycle.flags.stateful");
  const sandbox = metadata.sandboxed ? t("catalogControl.mcp.lifecycle.flags.sandboxed") : t("catalogControl.mcp.lifecycle.flags.unsandboxed");

  return t("catalogControl.mcp.lifecycle.summary", {
    category,
    risk,
    backingTool: backingToolName,
    exposureStatus,
    validationStatus: validationLabel,
    flags: [locality, statefulness, sandbox].join(", "),
  });
}
