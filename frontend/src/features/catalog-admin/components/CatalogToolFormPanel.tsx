import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import type { CatalogToolCreationOptions, CatalogToolExecutionBackend, CatalogToolMutationInput } from "../../../api/catalog";
import type { ToolFormState } from "../hooks/useCatalogControl";

type CatalogToolFormPanelProps = {
  form: ToolFormState;
  toolCreationOptions: CatalogToolCreationOptions | null;
  saving: boolean;
  onChange: (value: ToolFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onReset: () => void;
};

function stringifyJson(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2);
}

function formFromTemplate(
  form: ToolFormState,
  template: CatalogToolMutationInput,
  options: { selectedKnowledgeBaseId?: string } = {},
): ToolFormState {
  return {
    ...form,
    ...template,
    mode: form.mode,
    toolId: form.toolId,
    execution_backend: template.execution_backend ?? form.execution_backend,
    selectedKnowledgeBaseId: options.selectedKnowledgeBaseId ?? "",
    inputSchemaText: stringifyJson(template.input_schema),
    outputSchemaText: stringifyJson(template.output_schema),
    safetyPolicyText: stringifyJson(template.safety_policy),
    executionConfigText: stringifyJson(template.execution_config ?? {}),
    permissionsText: stringifyJson(template.permissions ?? {}),
  };
}

function backendLabelKey(executionBackend: string): string {
  if (executionBackend === "sandbox_python") {
    return "sandboxPython";
  }
  if (executionBackend === "mcp_gateway_web_search") {
    return "webSearch";
  }
  if (executionBackend === "knowledge_base_retrieval") {
    return "knowledgeBaseRetrieval";
  }
  return "internalHttp";
}

export default function CatalogToolFormPanel({
  form,
  toolCreationOptions,
  saving,
  onChange,
  onSubmit,
  onReset,
}: CatalogToolFormPanelProps): JSX.Element {
  const { t } = useTranslation("common");
  const backendOptions = toolCreationOptions?.execution_backends ?? [];
  const selectedBackend = backendOptions.find((option) => option.execution_backend === form.execution_backend) ?? null;
  const knowledgeBases = selectedBackend?.knowledge_bases ?? toolCreationOptions?.knowledge_bases ?? [];
  const requiresKnowledgeBase = form.execution_backend === "knowledge_base_retrieval";
  const detailsReady = form.mode === "edit" || Boolean(form.execution_backend && (!requiresKnowledgeBase || form.selectedKnowledgeBaseId));

  function handleBackendChange(executionBackend: string): void {
    const normalizedBackend = executionBackend as CatalogToolExecutionBackend | "";
    if (form.mode === "edit") {
      onChange({ ...form, execution_backend: normalizedBackend });
      return;
    }
    const option = backendOptions.find((item) => item.execution_backend === normalizedBackend);
    if (!option || !normalizedBackend) {
      onChange({
        ...form,
        execution_backend: "",
        selectedKnowledgeBaseId: "",
      });
      return;
    }
    if (option.requires_knowledge_base) {
      const defaultKnowledgeBaseId = toolCreationOptions?.selection_required
        ? ""
        : toolCreationOptions?.default_knowledge_base_id ?? option.knowledge_bases?.[0]?.id ?? "";
      const template = defaultKnowledgeBaseId ? option.templates_by_knowledge_base_id?.[defaultKnowledgeBaseId] : undefined;
      if (template) {
        onChange(formFromTemplate(form, template, { selectedKnowledgeBaseId: defaultKnowledgeBaseId }));
        return;
      }
      onChange({
        ...form,
        execution_backend: normalizedBackend,
        selectedKnowledgeBaseId: "",
        id: "",
        name: "",
        description: "",
        input_schema: {},
        output_schema: {},
        safety_policy: {},
        execution_config: {},
        permissions: {},
        inputSchemaText: "{}",
        outputSchemaText: "{}",
        safetyPolicyText: "{}",
        executionConfigText: "{}",
        permissionsText: "{}",
      });
      return;
    }
    if (option.template) {
      onChange(formFromTemplate(form, option.template));
      return;
    }
    onChange({ ...form, execution_backend: normalizedBackend });
  }

  function handleKnowledgeBaseChange(knowledgeBaseId: string): void {
    const template = selectedBackend?.templates_by_knowledge_base_id?.[knowledgeBaseId];
    if (template) {
      onChange(formFromTemplate(form, template, { selectedKnowledgeBaseId: knowledgeBaseId }));
      return;
    }
    onChange({ ...form, selectedKnowledgeBaseId: knowledgeBaseId });
  }

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h3 className="section-title">{t("catalogControl.tools.createTitle")}</h3>
        <p className="status-text">
          {form.mode === "create" ? t("catalogControl.tools.createDescription") : t("catalogControl.tools.editing")}
        </p>
      </div>

      <form className="card-stack" onSubmit={onSubmit}>
        <section className="panel panel-nested card-stack">
          <h4 className="section-title">{t("catalogControl.tools.steps.executionBackend")}</h4>
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.tool.executionBackend")}</span>
            <select
              className="field-input"
              value={form.execution_backend}
              disabled={form.mode === "edit"}
              onChange={(event) => handleBackendChange(event.target.value)}
            >
              <option value="">{t("catalogControl.forms.tool.noExecutionBackend")}</option>
              {backendOptions.map((option) => (
                <option key={option.execution_backend} value={option.execution_backend}>
                  {t(`catalogControl.executionBackend.${backendLabelKey(option.execution_backend)}`)}
                </option>
              ))}
            </select>
          </label>
          {requiresKnowledgeBase ? (
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.forms.tool.knowledgeBase")}</span>
              <select className="field-input" value={form.selectedKnowledgeBaseId} onChange={(event) => handleKnowledgeBaseChange(event.target.value)}>
                <option value="">{t("catalogControl.forms.tool.noKnowledgeBase")}</option>
                {knowledgeBases.map((knowledgeBase) => (
                  <option key={knowledgeBase.id} value={knowledgeBase.id}>
                    {knowledgeBase.display_name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          {requiresKnowledgeBase && knowledgeBases.length === 0 ? (
            <p className="status-text">{toolCreationOptions?.configuration_message ?? t("catalogControl.tools.noKnowledgeBases")}</p>
          ) : null}
        </section>

        {detailsReady ? (
          <>
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
          </>
        ) : null}
        <div className="status-row">
          <button type="submit" className="btn btn-primary" disabled={saving || !detailsReady}>
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
