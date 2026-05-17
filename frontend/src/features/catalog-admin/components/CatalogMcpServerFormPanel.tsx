import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import type { CatalogMcpCreationOptions, CatalogMcpServer, CatalogMcpServerSpec, CatalogTool } from "../../../api/catalog";
import type { McpServerFormState } from "../hooks/useCatalogControl";

type CatalogMcpServerFormPanelProps = {
  form: McpServerFormState;
  tools: CatalogTool[];
  mcpServers: CatalogMcpServer[];
  mcpCreationOptions: CatalogMcpCreationOptions | null;
  saving: boolean;
  onChange: (value: McpServerFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

const METADATA_CATEGORY_OPTIONS: CatalogMcpServerSpec["metadata"]["category"][] = [
  "web_search",
  "knowledge_retrieval",
  "code_execution",
  "data_analysis",
  "automation",
  "communication",
  "custom",
];
const RISK_LEVEL_OPTIONS: CatalogMcpServerSpec["metadata"]["risk_level"][] = ["low", "medium", "high"];
const DATA_ACCESS_OPTIONS: CatalogMcpServerSpec["metadata"]["data_access"][] = ["none", "public_web", "workspace", "user_data", "secrets_or_credentials"];
const OUTPUT_FRESHNESS_OPTIONS: CatalogMcpServerSpec["metadata"]["output_freshness"][] = ["static", "fresh", "runtime_generated"];
const AUDIT_LEVEL_OPTIONS: CatalogMcpServerSpec["metadata"]["audit_level"][] = ["standard", "elevated"];

function toolKey(tool: CatalogTool): string {
  return tool.id.replace(/^tool[._-]?/i, "").trim() || tool.id;
}

function slugFromTool(tool: CatalogTool): string {
  const normalized = toolKey(tool)
    .replace(/[^a-zA-Z0-9_.-]+/g, "_")
    .replace(/^[^a-zA-Z0-9]+/, "")
    .replace(/_+/g, "_")
    .toLowerCase();
  return normalized || "mcp_tool";
}

function uniqueValue(base: string, existingValues: Set<string>): string {
  if (!existingValues.has(base)) {
    return base;
  }
  let counter = 2;
  let candidate = `${base}_${counter}`;
  while (existingValues.has(candidate)) {
    counter += 1;
    candidate = `${base}_${counter}`;
  }
  return candidate;
}

function fallbackMetadataDefaultsForTool(tool: CatalogTool): CatalogMcpServerSpec["metadata"] {
  return {
    category: "custom",
    capabilities: [],
    local: Boolean(tool.spec.offline_compatible),
    stateless: true,
    sandboxed: false,
    risk_level: "medium",
    data_access: "none",
    output_freshness: "runtime_generated",
    audit_level: "standard",
  };
}

function metadataDefaultsForTool(tool: CatalogTool, mcpCreationOptions: CatalogMcpCreationOptions | null): CatalogMcpServerSpec["metadata"] {
  return mcpCreationOptions?.tools.find((item) => item.tool_id === tool.id)?.metadata_defaults ?? fallbackMetadataDefaultsForTool(tool);
}

function buildDefaultsForTool(
  tool: CatalogTool,
  mcpServers: CatalogMcpServer[],
  currentServerId: string,
  mcpCreationOptions: CatalogMcpCreationOptions | null,
): Partial<McpServerFormState> {
  const existingIds = new Set(mcpServers.filter((server) => server.id !== currentServerId).map((server) => server.id));
  const existingSlugs = new Set(mcpServers.filter((server) => server.id !== currentServerId).map((server) => server.spec.slug));
  const baseSlug = slugFromTool(tool);
  const slug = uniqueValue(baseSlug, existingSlugs);
  const id = uniqueValue(`mcp.${baseSlug}`, existingIds);
  const inputSchemaText = JSON.stringify(tool.spec.input_schema, null, 2);
  const outputSchemaText = JSON.stringify(tool.spec.output_schema, null, 2);
  const metadata = metadataDefaultsForTool(tool, mcpCreationOptions);
  return {
    id,
    mcpServerId: id,
    name: `${tool.spec.name} MCP`,
    slug,
    description: `Expose ${tool.spec.name} through the MCP gateway.`,
    backing_tool_id: tool.id,
    exposed_tool_name: slug,
    input_schema: tool.spec.input_schema,
    output_schema: tool.spec.output_schema,
    metadata,
    inputSchemaText,
    outputSchemaText,
    capabilitiesText: metadata.capabilities.join(", "),
  };
}

export default function CatalogMcpServerFormPanel({
  form,
  tools,
  mcpServers,
  mcpCreationOptions,
  saving,
  onChange,
  onSubmit,
}: CatalogMcpServerFormPanelProps): JSX.Element {
  const { t } = useTranslation("common");
  const eligibleTools = tools.filter((tool) =>
    tool.published
    && tool.validation_status?.last_validation_status === "success"
    && tool.validation_status?.is_validation_current
  );
  const backingTool = tools.find((tool) => tool.id === form.backing_tool_id) ?? null;
  const selectedTool = form.mode === "edit" ? backingTool : eligibleTools.find((tool) => tool.id === form.backing_tool_id) ?? null;
  const backingToolOptions = form.mode === "edit" && backingTool && !eligibleTools.some((tool) => tool.id === backingTool.id)
    ? [backingTool, ...eligibleTools]
    : eligibleTools;
  const title = form.mode === "create"
    ? t("catalogControl.mcp.createTitle")
    : t("catalogControl.mcp.editTitle", { name: form.name || form.mcpServerId });
  const description = form.mode === "create"
    ? t("catalogControl.mcp.createDescription")
    : t("catalogControl.mcp.editDescription", { name: form.name || form.mcpServerId });

  function handleBackingToolChange(toolId: string): void {
    if (form.mode === "edit") {
      return;
    }

    const selected = eligibleTools.find((tool) => tool.id === toolId);
    if (!selected) {
      onChange({
        ...form,
        backing_tool_id: "",
      });
      return;
    }

    onChange({
      ...form,
      ...buildDefaultsForTool(selected, mcpServers, form.mcpServerId, mcpCreationOptions),
    });
  }

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h3 className="section-title">{title}</h3>
        <p className="status-text">{description}</p>
      </div>
      <form className="card-stack" onSubmit={onSubmit}>
        <section className="panel panel-nested card-stack">
          <div className="status-row">
            <h4 className="section-title">{t("catalogControl.mcp.steps.backingTool")}</h4>
            {selectedTool ? (
              <span className="platform-badge">{selectedTool.spec.execution_backend ?? "internal_http"}</span>
            ) : null}
          </div>
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.mcp.backingTool")}</span>
            <select
              className="field-input"
              value={form.backing_tool_id}
              disabled={form.mode === "edit"}
              onChange={(event) => handleBackingToolChange(event.target.value)}
            >
              <option value="">{t("catalogControl.forms.mcp.noBackingTool")}</option>
              {backingToolOptions.map((tool) => (
                <option key={tool.id} value={tool.id}>{tool.spec.name}</option>
              ))}
            </select>
          </label>
          {eligibleTools.length === 0 ? (
            <p className="status-text">{t("catalogControl.mcp.noEligibleTools")}</p>
          ) : null}
          {selectedTool ? (
            <p className="status-text">
              {t("catalogControl.mcp.selectedToolMeta", {
                toolId: selectedTool.id,
                backend: selectedTool.spec.execution_backend ?? "internal_http",
              })}
            </p>
          ) : (
            <p className="status-text">{t("catalogControl.mcp.chooseToolFirst")}</p>
          )}
        </section>

        {selectedTool ? (
          <>
            <section className="panel panel-nested card-stack">
              <h4 className="section-title">{t("catalogControl.mcp.steps.identity")}</h4>
              <div className="form-grid">
                <label className="card-stack">
                  <span className="field-label">{t("catalogControl.forms.mcp.id")}</span>
                  <input className="field-input" value={form.id} disabled={form.mode === "edit"} onChange={(event) => onChange({ ...form, id: event.target.value })} />
                </label>
                <label className="card-stack">
                  <span className="field-label">{t("catalogControl.forms.mcp.name")}</span>
                  <input className="field-input" value={form.name} onChange={(event) => onChange({ ...form, name: event.target.value })} />
                </label>
                <label className="card-stack">
                  <span className="field-label">{t("catalogControl.forms.mcp.slug")}</span>
                  <input className="field-input" value={form.slug} disabled={form.mode === "edit"} onChange={(event) => onChange({ ...form, slug: event.target.value })} />
                </label>
                <label className="card-stack">
                  <span className="field-label">{t("catalogControl.forms.mcp.exposedToolName")}</span>
                  <input className="field-input" value={form.exposed_tool_name} onChange={(event) => onChange({ ...form, exposed_tool_name: event.target.value })} />
                </label>
                <label className="card-stack">
                  <span className="field-label">{t("catalogControl.forms.mcp.enabled")}</span>
                  <select className="field-input" value={form.enabled ? "true" : "false"} onChange={(event) => onChange({ ...form, enabled: event.target.value === "true" })}>
                    <option value="true">{t("catalogControl.badges.enabled")}</option>
                    <option value="false">{t("catalogControl.badges.disabled")}</option>
                  </select>
                </label>
                <label className="card-stack">
                  <span className="field-label">{t("catalogControl.forms.status")}</span>
                  <select className="field-input" value={form.publish ? "published" : "draft"} onChange={(event) => onChange({ ...form, publish: event.target.value === "published" })}>
                    <option value="draft">{t("catalogControl.badges.draft")}</option>
                    <option value="published">{t("catalogControl.badges.published")}</option>
                  </select>
                </label>
              </div>
              <label className="card-stack">
                <span className="field-label">{t("catalogControl.forms.mcp.description")}</span>
                <textarea className="field-input form-textarea" value={form.description} onChange={(event) => onChange({ ...form, description: event.target.value })} />
              </label>
            </section>

            <section className="panel panel-nested card-stack">
              <h4 className="section-title">{t("catalogControl.mcp.steps.metadata")}</h4>
              <div className="form-grid">
                <label className="card-stack">
                  <span className="field-label">{t("catalogControl.forms.mcp.category")}</span>
                  <select className="field-input" value={form.metadata.category} onChange={(event) => onChange({ ...form, metadata: { ...form.metadata, category: event.target.value as CatalogMcpServerSpec["metadata"]["category"] } })}>
                    {METADATA_CATEGORY_OPTIONS.map((option) => <option key={option} value={option}>{t(`catalogControl.mcp.metadata.category.${option}`)}</option>)}
                  </select>
                </label>
                <label className="card-stack">
                  <span className="field-label">{t("catalogControl.forms.mcp.local")}</span>
                  <select className="field-input" value={form.metadata.local ? "true" : "false"} onChange={(event) => onChange({ ...form, metadata: { ...form.metadata, local: event.target.value === "true" } })}>
                    <option value="true">{t("catalogControl.badges.yes")}</option>
                    <option value="false">{t("catalogControl.badges.no")}</option>
                  </select>
                </label>
                <label className="card-stack">
                  <span className="field-label">{t("catalogControl.forms.mcp.stateless")}</span>
                  <select className="field-input" value={form.metadata.stateless ? "true" : "false"} onChange={(event) => onChange({ ...form, metadata: { ...form.metadata, stateless: event.target.value === "true" } })}>
                    <option value="true">{t("catalogControl.badges.yes")}</option>
                    <option value="false">{t("catalogControl.badges.no")}</option>
                  </select>
                </label>
                <label className="card-stack">
                  <span className="field-label">{t("catalogControl.forms.mcp.sandboxed")}</span>
                  <select className="field-input" value={form.metadata.sandboxed ? "true" : "false"} onChange={(event) => onChange({ ...form, metadata: { ...form.metadata, sandboxed: event.target.value === "true" } })}>
                    <option value="true">{t("catalogControl.badges.yes")}</option>
                    <option value="false">{t("catalogControl.badges.no")}</option>
                  </select>
                </label>
                <label className="card-stack">
                  <span className="field-label">{t("catalogControl.forms.mcp.riskLevel")}</span>
                  <select className="field-input" value={form.metadata.risk_level} onChange={(event) => onChange({ ...form, metadata: { ...form.metadata, risk_level: event.target.value as CatalogMcpServerSpec["metadata"]["risk_level"] } })}>
                    {RISK_LEVEL_OPTIONS.map((option) => <option key={option} value={option}>{t(`catalogControl.mcp.metadata.riskLevel.${option}`)}</option>)}
                  </select>
                </label>
                <label className="card-stack">
                  <span className="field-label">{t("catalogControl.forms.mcp.dataAccess")}</span>
                  <select className="field-input" value={form.metadata.data_access} onChange={(event) => onChange({ ...form, metadata: { ...form.metadata, data_access: event.target.value as CatalogMcpServerSpec["metadata"]["data_access"] } })}>
                    {DATA_ACCESS_OPTIONS.map((option) => <option key={option} value={option}>{t(`catalogControl.mcp.metadata.dataAccess.${option}`)}</option>)}
                  </select>
                </label>
                <label className="card-stack">
                  <span className="field-label">{t("catalogControl.forms.mcp.outputFreshness")}</span>
                  <select className="field-input" value={form.metadata.output_freshness} onChange={(event) => onChange({ ...form, metadata: { ...form.metadata, output_freshness: event.target.value as CatalogMcpServerSpec["metadata"]["output_freshness"] } })}>
                    {OUTPUT_FRESHNESS_OPTIONS.map((option) => <option key={option} value={option}>{t(`catalogControl.mcp.metadata.outputFreshness.${option}`)}</option>)}
                  </select>
                </label>
                <label className="card-stack">
                  <span className="field-label">{t("catalogControl.forms.mcp.auditLevel")}</span>
                  <select className="field-input" value={form.metadata.audit_level} onChange={(event) => onChange({ ...form, metadata: { ...form.metadata, audit_level: event.target.value as CatalogMcpServerSpec["metadata"]["audit_level"] } })}>
                    {AUDIT_LEVEL_OPTIONS.map((option) => <option key={option} value={option}>{t(`catalogControl.mcp.metadata.auditLevel.${option}`)}</option>)}
                  </select>
                </label>
              </div>
              <label className="card-stack">
                <span className="field-label">{t("catalogControl.forms.mcp.capabilities")}</span>
                <input className="field-input" value={form.capabilitiesText} onChange={(event) => onChange({ ...form, capabilitiesText: event.target.value })} />
              </label>
            </section>

            <section className="panel panel-nested card-stack">
              <h4 className="section-title">{t("catalogControl.mcp.steps.schemas")}</h4>
              <label className="card-stack">
                <span className="field-label">{t("catalogControl.forms.mcp.inputSchema")}</span>
                <textarea className="field-input form-textarea" value={form.inputSchemaText} onChange={(event) => onChange({ ...form, inputSchemaText: event.target.value })} />
              </label>
              <label className="card-stack">
                <span className="field-label">{t("catalogControl.forms.mcp.outputSchema")}</span>
                <textarea className="field-input form-textarea" value={form.outputSchemaText} onChange={(event) => onChange({ ...form, outputSchemaText: event.target.value })} />
              </label>
            </section>

            <section className="panel panel-nested card-stack">
              <h4 className="section-title">{t("catalogControl.mcp.steps.accessPolicy")}</h4>
              <div className="form-grid">
                <label className="card-stack"><span className="field-label">{t("catalogControl.forms.mcp.agentDomains")}</span><input className="field-input" value={form.agentDomainsText} onChange={(event) => onChange({ ...form, agentDomainsText: event.target.value })} /></label>
                <label className="card-stack"><span className="field-label">{t("catalogControl.forms.mcp.agentIds")}</span><input className="field-input" value={form.agentIdsText} onChange={(event) => onChange({ ...form, agentIdsText: event.target.value })} /></label>
                <label className="card-stack"><span className="field-label">{t("catalogControl.forms.mcp.agentRoles")}</span><input className="field-input" value={form.agentRolesText} onChange={(event) => onChange({ ...form, agentRolesText: event.target.value })} /></label>
                <label className="card-stack"><span className="field-label">{t("catalogControl.forms.mcp.userRoles")}</span><input className="field-input" value={form.userRolesText} onChange={(event) => onChange({ ...form, userRolesText: event.target.value })} /></label>
                <label className="card-stack"><span className="field-label">{t("catalogControl.forms.mcp.userIds")}</span><input className="field-input" value={form.userIdsText} onChange={(event) => onChange({ ...form, userIdsText: event.target.value })} /></label>
                <label className="card-stack"><span className="field-label">{t("catalogControl.forms.mcp.userGroupIds")}</span><input className="field-input" value={form.userGroupIdsText} onChange={(event) => onChange({ ...form, userGroupIdsText: event.target.value })} /></label>
              </div>
            </section>
          </>
        ) : null}
        <div className="status-row">
          <button type="submit" className="btn btn-primary" disabled={saving || !selectedTool}>{saving ? t("catalogControl.actions.saving") : t(form.mode === "create" ? "catalogControl.actions.createMcpServer" : "catalogControl.actions.updateMcpServer")}</button>
        </div>
      </form>
    </article>
  );
}
