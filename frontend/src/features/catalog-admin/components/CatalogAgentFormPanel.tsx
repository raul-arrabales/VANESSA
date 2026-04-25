import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import type { CatalogTool } from "../../../api/catalog";
import type { ModelCatalogItem } from "../../../api/modelops";
import { buildAgentSystemPromptPreview, type AgentFormState } from "../hooks/useCatalogControl";

type CatalogAgentFormPanelProps = {
  form: AgentFormState;
  tools: CatalogTool[];
  models: ModelCatalogItem[];
  saving: boolean;
  onChange: (value: AgentFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onReset: () => void;
};

export default function CatalogAgentFormPanel({
  form,
  tools,
  models,
  saving,
  onChange,
  onSubmit,
  onReset,
}: CatalogAgentFormPanelProps): JSX.Element {
  const { t } = useTranslation("common");
  const promptPreview = buildAgentSystemPromptPreview(form);

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h3 className="section-title">{t("catalogControl.agents.createTitle")}</h3>
        <p className="status-text">
          {form.mode === "create" ? t("catalogControl.agents.createDescription") : t("catalogControl.agents.editing")}
        </p>
      </div>

      <form className="card-stack" onSubmit={onSubmit}>
        <div className="form-grid">
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.agent.id")}</span>
            <input
              className="field-input"
              value={form.id}
              disabled={form.mode === "edit"}
              onChange={(event) => onChange({ ...form, id: event.target.value })}
            />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.agent.name")}</span>
            <input className="field-input" value={form.name} onChange={(event) => onChange({ ...form, name: event.target.value })} />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.agent.defaultModel")}</span>
            <select
              className="field-input"
              value={form.default_model_ref ?? ""}
              onChange={(event) => onChange({ ...form, default_model_ref: event.target.value || null })}
            >
              <option value="">{t("catalogControl.forms.agent.noDefaultModel")}</option>
              {models.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name}
                </option>
              ))}
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
        </div>
        <label className="card-stack">
          <span className="field-label">{t("catalogControl.forms.agent.description")}</span>
          <textarea className="field-input form-textarea" value={form.description} onChange={(event) => onChange({ ...form, description: event.target.value })} />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("catalogControl.forms.agent.instructions")}</span>
          <textarea className="field-input form-textarea" value={form.instructions} onChange={(event) => onChange({ ...form, instructions: event.target.value })} />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("catalogControl.forms.agent.retrievalInstructions")}</span>
          <textarea
            className="field-input form-textarea"
            value={form.runtime_prompts.retrieval_context}
            onChange={(event) =>
              onChange({
                ...form,
                runtime_prompts: {
                  ...form.runtime_prompts,
                  retrieval_context: event.target.value,
                },
              })
            }
          />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("catalogControl.forms.agent.promptReview")}</span>
          <textarea className="field-input form-textarea catalog-prompt-review" value={promptPreview} readOnly />
        </label>
        <label className="card-stack">
          <span className="field-label">{t("catalogControl.forms.agent.toolRefs")}</span>
          <select
            className="field-input catalog-multiselect"
            multiple
            value={form.tool_refs}
            onChange={(event) =>
              onChange({
                ...form,
                tool_refs: Array.from(event.currentTarget.selectedOptions).map((option) => option.value),
              })
            }
          >
            {tools.map((tool) => (
              <option key={tool.id} value={tool.id}>
                {tool.spec.name}
              </option>
            ))}
          </select>
        </label>
        <div className="form-grid">
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.agent.internetRequired")}</span>
            <select
              className="field-input"
              value={form.runtime_constraints.internet_required ? "true" : "false"}
              onChange={(event) =>
                onChange({
                  ...form,
                  runtime_constraints: {
                    ...form.runtime_constraints,
                    internet_required: event.target.value === "true",
                  },
                })
              }
            >
              <option value="false">{t("catalogControl.badges.no")}</option>
              <option value="true">{t("catalogControl.badges.yes")}</option>
            </select>
          </label>
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.agent.sandboxRequired")}</span>
            <select
              className="field-input"
              value={form.runtime_constraints.sandbox_required ? "true" : "false"}
              onChange={(event) =>
                onChange({
                  ...form,
                  runtime_constraints: {
                    ...form.runtime_constraints,
                    sandbox_required: event.target.value === "true",
                  },
                })
              }
            >
              <option value="false">{t("catalogControl.badges.no")}</option>
              <option value="true">{t("catalogControl.badges.yes")}</option>
            </select>
          </label>
        </div>
        <div className="status-row">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? t("catalogControl.actions.saving") : t(form.mode === "create" ? "catalogControl.actions.createAgent" : "catalogControl.actions.updateAgent")}
          </button>
          <button type="button" className="btn btn-secondary" onClick={onReset}>
            {t("catalogControl.actions.newAgent")}
          </button>
        </div>
      </form>
    </article>
  );
}
