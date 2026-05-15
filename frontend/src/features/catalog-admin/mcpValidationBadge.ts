import type { TFunction } from "i18next";
import type { CatalogMcpServer, CatalogMcpServerValidation } from "../../api/catalog";

export type McpValidationBadge = {
  label: string;
  tone: "active" | "inactive" | "optional" | "required";
};

export function getMcpValidationBadge(
  server: CatalogMcpServer,
  validation: CatalogMcpServerValidation["validation"] | undefined,
  isValidating: boolean,
  t: TFunction<"common">,
): McpValidationBadge {
  if (isValidating) {
    return {
      label: t("catalogControl.mcp.validationBadges.validating"),
      tone: "optional",
    };
  }
  if (validation) {
    return validation.valid
      ? { label: t("catalogControl.mcp.validationBadges.validated"), tone: "active" }
      : { label: t("catalogControl.mcp.validationBadges.failed"), tone: "inactive" };
  }

  const validationStatus = server.validation_status;
  const lastValidationStatus = String(validationStatus.last_validation_status || "unknown").toLowerCase();
  if (lastValidationStatus === "success" && validationStatus.is_validation_current) {
    return {
      label: t("catalogControl.mcp.validationBadges.validated"),
      tone: "active",
    };
  }
  if (lastValidationStatus === "failed") {
    return {
      label: t("catalogControl.mcp.validationBadges.failed"),
      tone: "inactive",
    };
  }
  if (lastValidationStatus === "success" && !validationStatus.is_validation_current) {
    return {
      label: t("catalogControl.mcp.validationBadges.stale"),
      tone: "optional",
    };
  }
  return {
    label: t("catalogControl.mcp.validationBadges.unvalidated"),
    tone: "required",
  };
}
