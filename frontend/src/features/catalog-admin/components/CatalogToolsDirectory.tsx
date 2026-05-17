import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import IconButton from "../../../components/IconButton";
import type { CatalogTool, CatalogToolValidation } from "../../../api/catalog";
import { catalogToolBackendLabelKey } from "../catalogToolBackends";
import CatalogMcpRegistryIcon from "./CatalogMcpRegistryIcon";

type CatalogToolsDirectoryProps = {
  tools: CatalogTool[];
  validationResults: Record<string, CatalogToolValidation>;
  validatingToolId: string;
  onEdit: (tool: CatalogTool) => void;
  onTest: (tool: CatalogTool) => void;
  onValidate: (toolId: string) => void;
};

type ToolValidationBadge = {
  label: string;
  tone: "active" | "inactive" | "optional" | "required";
};

function getToolValidationBadge(
  tool: CatalogTool,
  validation: CatalogToolValidation["validation"] | undefined,
  isValidating: boolean,
  t: TFunction<"common">,
): ToolValidationBadge {
  if (isValidating) {
    return {
      label: t("catalogControl.tools.validationBadges.validating"),
      tone: "optional",
    };
  }
  if (validation) {
    return validation.valid
      ? { label: t("catalogControl.tools.validationBadges.validated"), tone: "active" }
      : { label: t("catalogControl.tools.validationBadges.failed"), tone: "inactive" };
  }

  const validationStatus = tool.validation_status;
  const lastValidationStatus = String(validationStatus?.last_validation_status || "unknown").toLowerCase();
  if (lastValidationStatus === "success" && validationStatus?.is_validation_current) {
    return {
      label: t("catalogControl.tools.validationBadges.validated"),
      tone: "active",
    };
  }
  if (lastValidationStatus === "failed") {
    return {
      label: t("catalogControl.tools.validationBadges.failed"),
      tone: "inactive",
    };
  }
  if (lastValidationStatus === "success" && !validationStatus?.is_validation_current) {
    return {
      label: t("catalogControl.tools.validationBadges.stale"),
      tone: "optional",
    };
  }
  return {
    label: t("catalogControl.tools.validationBadges.unvalidated"),
    tone: "required",
  };
}

export default function CatalogToolsDirectory({
  tools,
  validationResults,
  validatingToolId,
  onEdit,
  onTest,
  onValidate,
}: CatalogToolsDirectoryProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h3 className="section-title">{t("catalogControl.tools.listTitle")}</h3>
        <p className="status-text">{t("catalogControl.tools.description")}</p>
      </div>

      <div className="catalog-mcp-registry-list" role="list">
        {tools.map((tool) => {
          const validation = validationResults[tool.id]?.validation;
          const isValidating = validatingToolId === tool.id;
          const validationBadge = getToolValidationBadge(tool, validation, isValidating, t);
          const backendLabel = t(`catalogControl.executionBackend.${catalogToolBackendLabelKey(tool.spec.execution_backend)}`);
          const validateLabel = isValidating
            ? t("catalogControl.tools.actionLabels.validating", { name: tool.spec.name })
            : t("catalogControl.tools.actionLabels.validate", { name: tool.spec.name });
          return (
            <article key={tool.id} className="catalog-mcp-registry-item" role="listitem">
              <div className="catalog-mcp-registry-main">
                <div className="catalog-mcp-registry-heading">
                  <h4 className="section-title">{tool.spec.name}</h4>
                  <span className="platform-badge" data-tone={tool.published ? "active" : "required"}>
                    {tool.published ? t("catalogControl.badges.published") : t("catalogControl.badges.draft")}
                  </span>
                  <span className="platform-badge" data-tone={validationBadge.tone}>
                    {validationBadge.label}
                  </span>
                  <span className="platform-badge">{backendLabel}</span>
                  <span className="platform-badge" data-tone={tool.spec.offline_compatible ? "active" : "optional"}>
                    {tool.spec.offline_compatible
                      ? t("catalogControl.tools.offlineCompatible")
                      : t("catalogControl.tools.networkRequired")}
                  </span>
                </div>
                <p className="status-text catalog-mcp-description-preview">{tool.spec.description}</p>
                <div className="catalog-mcp-meta-row">
                  <code className="code-inline">{tool.id}</code>
                  <span>{t("catalogControl.tools.backendLabel", { backend: backendLabel })}</span>
                  <span>
                    {t("catalogControl.tools.updatedLabel", {
                      updated: tool.updated_at ?? tool.published_at ?? "-",
                    })}
                  </span>
                </div>
              </div>
              <div className="catalog-mcp-registry-actions" role="group" aria-label={t("catalogControl.tools.actionsFor", { name: tool.spec.name })}>
                <IconButton label={t("catalogControl.tools.actionLabels.edit", { name: tool.spec.name })} onClick={() => onEdit(tool)}>
                  <CatalogMcpRegistryIcon name="edit" />
                </IconButton>
                <IconButton label={t("catalogControl.tools.actionLabels.test", { name: tool.spec.name })} onClick={() => onTest(tool)}>
                  <CatalogMcpRegistryIcon name="test" />
                </IconButton>
                <IconButton label={validateLabel} onClick={() => onValidate(tool.id)} disabled={isValidating}>
                  <CatalogMcpRegistryIcon name="validate" />
                </IconButton>
              </div>
              {validation ? (
                <div className="catalog-mcp-validation">
                  <span className="field-label">
                    {validation.valid ? t("catalogControl.validation.valid") : t("catalogControl.validation.invalid")}
                  </span>
                  {validation.errors.length > 0 ? (
                    <ul className="status-text">
                      {validation.errors.map((message) => (
                        <li key={message}>{message}</li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </article>
  );
}
