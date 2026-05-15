import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import type { ToolFormState } from "../hooks/useCatalogControl";

type CatalogToolFormPanelProps = {
  form: ToolFormState;
  saving: boolean;
  onChange: (value: ToolFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onReset: () => void;
};

export default function CatalogToolFormPanel({
  form,
  saving,
  onChange,
  onSubmit,
  onReset,
}: CatalogToolFormPanelProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h3 className="section-title">{t("catalogControl.tools.createTitle")}</h3>
        <p className="status-text">
          {form.mode === "create" ? t("catalogControl.tools.createDescription") : t("catalogControl.tools.editing")}
        </p>
      </div>

      <form className="card-stack" onSubmit={onSubmit}>
        <div className="form-grid">
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.tool.id")}</span>
            <input
              className="field-input"
              value={form.id}
              disabled={form.mode === "edit"}
              onChange={(event) => onChange({ ...form, id: event.target.value })}
            />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.tool.name")}</span>
            <input className="field-input" value={form.name} onChange={(event) => onChange({ ...form, name: event.target.value })} />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.tool.executionBackend")}</span>
            <select
              className="field-input"
              value={form.execution_backend}
              onChange={(event) => onChange({ ...form, execution_backend: event.target.value as ToolFormState["execution_backend"] })}
            >
              <option value="sandbox_python">{t("catalogControl.executionBackend.sandboxPython")}</option>
              <option value="mcp_gateway_web_search">{t("catalogControl.executionBackend.webSearch")}</option>
              <option value="internal_http">{t("catalogControl.executionBackend.internalHttp")}</option>
            </select>
          </label>
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.status")}</span>
            <select
              className="field-input"
              value={form.publish ? "published" : "draft"}
              onChange={(event) => onChange({ ...form, publish: event.target.value === "published" })}
            >
              <option value="draft">{t("catalogControl.badges.draft")}</option>
              <option value="published">{t("catalogControl.badges.published")}</option>
            </select>
          </label>
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.tool.offlineCompatible")}</span>
            <select
              className="field-input"
              value={form.offline_compatible ? "true" : "false"}
              onChange={(event) => onChange({ ...form, offline_compatible: event.target.value === "true" })}
            >
              <option value="false">{t("catalogControl.badges.no")}</option>
              <option value="true">{t("catalogControl.badges.yes")}</option>
            </select>
          </label>
        </div>
        <label className="card-stack">
          <span className="field-label">{t("catalogControl.forms.tool.description")}</span>
          <textarea className="field-input form-textarea" value={form.description} onChange={(event) => onChange({ ...form, description: event.target.value })} />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("catalogControl.forms.tool.inputSchema")}</span>
          <textarea className="field-input form-textarea" value={form.inputSchemaText} onChange={(event) => onChange({ ...form, inputSchemaText: event.target.value })} />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("catalogControl.forms.tool.outputSchema")}</span>
          <textarea className="field-input form-textarea" value={form.outputSchemaText} onChange={(event) => onChange({ ...form, outputSchemaText: event.target.value })} />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("catalogControl.forms.tool.safetyPolicy")}</span>
          <textarea className="field-input form-textarea" value={form.safetyPolicyText} onChange={(event) => onChange({ ...form, safetyPolicyText: event.target.value })} />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("catalogControl.forms.tool.executionConfig")}</span>
          <textarea className="field-input form-textarea" value={form.executionConfigText} onChange={(event) => onChange({ ...form, executionConfigText: event.target.value })} />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("catalogControl.forms.tool.permissions")}</span>
          <textarea className="field-input form-textarea" value={form.permissionsText} onChange={(event) => onChange({ ...form, permissionsText: event.target.value })} />
        </label>
        <div className="status-row">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? t("catalogControl.actions.saving") : t(form.mode === "create" ? "catalogControl.actions.createTool" : "catalogControl.actions.updateTool")}
          </button>
          <button type="button" className="btn btn-secondary" onClick={onReset}>
            {t("catalogControl.actions.newTool")}
          </button>
        </div>
      </form>
    </article>
  );
}
