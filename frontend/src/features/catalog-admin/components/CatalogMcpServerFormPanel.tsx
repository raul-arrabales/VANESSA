import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import type { CatalogTool } from "../../../api/catalog";
import type { McpServerFormState } from "../hooks/useCatalogControl";

type CatalogMcpServerFormPanelProps = {
  form: McpServerFormState;
  tools: CatalogTool[];
  saving: boolean;
  onChange: (value: McpServerFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onReset: () => void;
};

export default function CatalogMcpServerFormPanel({
  form,
  tools,
  saving,
  onChange,
  onSubmit,
  onReset,
}: CatalogMcpServerFormPanelProps): JSX.Element {
  const { t } = useTranslation("common");
  const eligibleTools = tools.filter((tool) =>
    tool.published
    && tool.validation_status?.last_validation_status === "success"
    && tool.validation_status?.is_validation_current
  );

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h3 className="section-title">{t("catalogControl.mcp.createTitle")}</h3>
        <p className="status-text">{form.mode === "create" ? t("catalogControl.mcp.createDescription") : t("catalogControl.mcp.editing")}</p>
      </div>
      <form className="card-stack" onSubmit={onSubmit}>
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
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.mcp.exposedToolName")}</span>
            <input className="field-input" value={form.exposed_tool_name} onChange={(event) => onChange({ ...form, exposed_tool_name: event.target.value })} />
          </label>
        </div>
        <label className="card-stack">
          <span className="field-label">{t("catalogControl.forms.mcp.backingTool")}</span>
          <select
            className="field-input"
            value={form.backing_tool_id}
            onChange={(event) => {
              const selected = eligibleTools.find((tool) => tool.id === event.target.value);
              onChange({
                ...form,
                backing_tool_id: event.target.value,
                inputSchemaText: selected ? JSON.stringify(selected.spec.input_schema, null, 2) : form.inputSchemaText,
                outputSchemaText: selected ? JSON.stringify(selected.spec.output_schema, null, 2) : form.outputSchemaText,
              });
            }}
          >
            <option value="">{t("catalogControl.forms.mcp.noBackingTool")}</option>
            {eligibleTools.map((tool) => (
              <option key={tool.id} value={tool.id}>{tool.spec.name}</option>
            ))}
          </select>
        </label>
        <label className="card-stack">
          <span className="field-label">{t("catalogControl.forms.mcp.description")}</span>
          <textarea className="field-input form-textarea" value={form.description} onChange={(event) => onChange({ ...form, description: event.target.value })} />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("catalogControl.forms.mcp.inputSchema")}</span>
          <textarea className="field-input form-textarea" value={form.inputSchemaText} onChange={(event) => onChange({ ...form, inputSchemaText: event.target.value })} />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("catalogControl.forms.mcp.outputSchema")}</span>
          <textarea className="field-input form-textarea" value={form.outputSchemaText} onChange={(event) => onChange({ ...form, outputSchemaText: event.target.value })} />
        </label>
        <div className="form-grid">
          <label className="card-stack"><span className="field-label">{t("catalogControl.forms.mcp.agentDomains")}</span><input className="field-input" value={form.agentDomainsText} onChange={(event) => onChange({ ...form, agentDomainsText: event.target.value })} /></label>
          <label className="card-stack"><span className="field-label">{t("catalogControl.forms.mcp.agentIds")}</span><input className="field-input" value={form.agentIdsText} onChange={(event) => onChange({ ...form, agentIdsText: event.target.value })} /></label>
          <label className="card-stack"><span className="field-label">{t("catalogControl.forms.mcp.agentRoles")}</span><input className="field-input" value={form.agentRolesText} onChange={(event) => onChange({ ...form, agentRolesText: event.target.value })} /></label>
          <label className="card-stack"><span className="field-label">{t("catalogControl.forms.mcp.userRoles")}</span><input className="field-input" value={form.userRolesText} onChange={(event) => onChange({ ...form, userRolesText: event.target.value })} /></label>
          <label className="card-stack"><span className="field-label">{t("catalogControl.forms.mcp.userIds")}</span><input className="field-input" value={form.userIdsText} onChange={(event) => onChange({ ...form, userIdsText: event.target.value })} /></label>
          <label className="card-stack"><span className="field-label">{t("catalogControl.forms.mcp.userGroupIds")}</span><input className="field-input" value={form.userGroupIdsText} onChange={(event) => onChange({ ...form, userGroupIdsText: event.target.value })} /></label>
        </div>
        <div className="status-row">
          <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? t("catalogControl.actions.saving") : t(form.mode === "create" ? "catalogControl.actions.createMcpServer" : "catalogControl.actions.updateMcpServer")}</button>
          <button type="button" className="btn btn-secondary" onClick={onReset}>{t("catalogControl.actions.newMcpServer")}</button>
        </div>
      </form>
    </article>
  );
}
