import type { FormEvent } from "react";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import type { CatalogMcpServer } from "../../../api/catalog";
import type { ModelCatalogItem } from "../../../api/modelops";
import type { AgentProjectFormState } from "../../agent-builder/types";

type Props = {
  form: AgentProjectFormState;
  saving: boolean;
  mcpServers: CatalogMcpServer[];
  models: ModelCatalogItem[];
  onChange: (value: AgentProjectFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onReset: () => void;
};

export default function CatalogUserAgentBuilderPanel({
  form,
  saving,
  mcpServers,
  models,
  onChange,
  onSubmit,
  onReset,
}: Props): JSX.Element {
  const { t } = useTranslation("common");
  const selectedMcpServer = useMemo(
    () => mcpServers.find((server) => server.spec.slug === form.selectedMcpServerSlug) ?? null,
    [form.selectedMcpServerSlug, mcpServers],
  );

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <div className="card-stack">
          <h3 className="section-title">{t("catalogControl.agents.userProjects.createTitle")}</h3>
          <p className="status-text">{t("catalogControl.agents.userProjects.createDescription")}</p>
        </div>
        <button type="button" className="btn btn-secondary" onClick={onReset}>
          {t("catalogControl.actions.newAgent")}
        </button>
      </div>

      <form className="card-stack" onSubmit={onSubmit}>
        <section className="panel panel-nested card-stack">
          <h4 className="section-title">{t("catalogControl.agents.userProjects.stepType")}</h4>
          <div className="form-grid">
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.agents.userProjects.agentType")}</span>
              <select className="field-input" value={form.agentType} onChange={(event) => onChange({ ...form, agentType: event.currentTarget.value as AgentProjectFormState["agentType"] })}>
                <option value="workflow">Workflow Agent</option>
                <option value="planner" disabled>Planner Agent (Coming soon)</option>
                <option value="react" disabled>ReAct Agent (Coming soon)</option>
              </select>
            </label>
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.agents.userProjects.channelType")}</span>
              <input className="field-input" value="Vanessa WebApp" disabled />
            </label>
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.agents.userProjects.interfaceType")}</span>
              <input className="field-input" value="Chat" disabled />
            </label>
          </div>
        </section>

        <section className="panel panel-nested card-stack">
          <h4 className="section-title">{t("catalogControl.agents.userProjects.stepBasics")}</h4>
          <div className="form-grid">
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.forms.agent.id")}</span>
              <input className="field-input" value={form.id} onChange={(event) => onChange({ ...form, id: event.currentTarget.value })} />
            </label>
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.forms.agent.name")}</span>
              <input className="field-input" value={form.name} onChange={(event) => onChange({ ...form, name: event.currentTarget.value })} />
            </label>
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.forms.status")}</span>
              <select className="field-input" value={form.visibility} onChange={(event) => onChange({ ...form, visibility: event.currentTarget.value as AgentProjectFormState["visibility"] })}>
                <option value="private">private</option>
                <option value="unlisted">unlisted</option>
                <option value="public">public</option>
              </select>
            </label>
          </div>
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.agent.description")}</span>
            <textarea className="field-input form-textarea" value={form.description} onChange={(event) => onChange({ ...form, description: event.currentTarget.value })} />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.agent.instructions")}</span>
            <textarea className="field-input form-textarea" value={form.instructions} onChange={(event) => onChange({ ...form, instructions: event.currentTarget.value })} />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.agent.defaultModel")}</span>
            <select className="field-input" value={form.defaultModelRef} onChange={(event) => onChange({ ...form, defaultModelRef: event.currentTarget.value })}>
              <option value="">{t("catalogControl.forms.agent.noDefaultModel")}</option>
              {models.map((model) => (
                <option key={model.id} value={model.id}>{model.name}</option>
              ))}
            </select>
          </label>
        </section>

        <section className="panel panel-nested card-stack">
          <h4 className="section-title">{t("catalogControl.agents.userProjects.stepWorkflow")}</h4>
          <p className="status-text">{t("catalogControl.agents.userProjects.workflowHelp")}</p>
          <div className="form-grid">
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.agents.userProjects.workflowMcp")}</span>
              <select className="field-input" value={form.selectedMcpServerSlug} onChange={(event) => onChange({ ...form, selectedMcpServerSlug: event.currentTarget.value, selectedToolName: event.currentTarget.selectedOptions[0]?.dataset.toolName ?? form.selectedToolName, stepName: event.currentTarget.selectedOptions[0]?.dataset.serverName ?? form.stepName })}>
                <option value="">{t("catalogControl.agents.userProjects.selectMcp")}</option>
                {mcpServers.filter((server) => server.spec.enabled).map((server) => (
                  <option
                    key={server.id}
                    value={server.spec.slug}
                    data-tool-name={server.spec.exposed_tool_name}
                    data-server-name={server.spec.name}
                  >
                    {server.spec.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.agents.userProjects.workflowTool")}</span>
              <input className="field-input" value={form.selectedToolName || selectedMcpServer?.spec.exposed_tool_name || ""} onChange={(event) => onChange({ ...form, selectedToolName: event.currentTarget.value })} />
            </label>
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.agents.userProjects.workflowStepName")}</span>
              <input className="field-input" value={form.stepName} onChange={(event) => onChange({ ...form, stepName: event.currentTarget.value })} />
            </label>
          </div>
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.agents.userProjects.workflowArguments")}</span>
            <textarea className="field-input form-textarea" value={form.stepArgumentsText} onChange={(event) => onChange({ ...form, stepArgumentsText: event.currentTarget.value })} />
          </label>
        </section>

        <div className="status-row">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? t("catalogControl.actions.saving") : t("catalogControl.agents.userProjects.save")}
          </button>
        </div>
      </form>
    </article>
  );
}
