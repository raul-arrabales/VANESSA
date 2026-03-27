import { type FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../../auth/AuthProvider";
import {
  createCatalogAgent,
  createCatalogTool,
  listCatalogAgents,
  listCatalogTools,
  type CatalogAgent,
  type CatalogAgentMutationInput,
  type CatalogAgentValidation,
  type CatalogTool,
  type CatalogToolMutationInput,
  type CatalogToolValidation,
  updateCatalogAgent,
  updateCatalogTool,
  validateCatalogAgent,
  validateCatalogTool,
} from "../../../api/catalog";
import { listEnabledModels, type ModelCatalogItem } from "../../../api/modelops";
import { useActionFeedback } from "../../../feedback/ActionFeedbackProvider";

type LoadState = "idle" | "loading" | "success" | "error";
type FormMode = "create" | "edit";

type AgentFormState = CatalogAgentMutationInput & {
  mode: FormMode;
  agentId: string;
};

type ToolFormState = CatalogToolMutationInput & {
  mode: FormMode;
  toolId: string;
  inputSchemaText: string;
  outputSchemaText: string;
  safetyPolicyText: string;
};

const DEFAULT_AGENT_FORM: AgentFormState = {
  mode: "create",
  agentId: "",
  id: "",
  visibility: "private",
  publish: false,
  name: "",
  description: "",
  instructions: "",
  default_model_ref: null,
  tool_refs: [],
  runtime_constraints: {
    internet_required: false,
    sandbox_required: false,
  },
};

const DEFAULT_TOOL_FORM: ToolFormState = {
  mode: "create",
  toolId: "",
  id: "",
  visibility: "private",
  publish: false,
  name: "",
  description: "",
  transport: "mcp",
  connection_profile_ref: "default",
  tool_name: "",
  input_schema: {},
  output_schema: {},
  safety_policy: {},
  offline_compatible: false,
  inputSchemaText: "{}",
  outputSchemaText: "{}",
  safetyPolicyText: "{}",
};

function stringifyJson(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2);
}

function parseJsonObject(text: string, errorMessage: string): Record<string, unknown> {
  const normalized = text.trim();
  if (!normalized) {
    return {};
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(normalized);
  } catch {
    throw new Error(errorMessage);
  }

  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(errorMessage);
  }

  return parsed as Record<string, unknown>;
}

function buildAgentForm(agent: CatalogAgent): AgentFormState {
  return {
    mode: "edit",
    agentId: agent.id,
    id: agent.id,
    visibility: agent.entity.visibility,
    publish: agent.published,
    name: agent.spec.name,
    description: agent.spec.description,
    instructions: agent.spec.instructions,
    default_model_ref: agent.spec.default_model_ref,
    tool_refs: agent.spec.tool_refs,
    runtime_constraints: {
      internet_required: agent.spec.runtime_constraints.internet_required,
      sandbox_required: agent.spec.runtime_constraints.sandbox_required,
    },
  };
}

function buildToolForm(tool: CatalogTool): ToolFormState {
  return {
    mode: "edit",
    toolId: tool.id,
    id: tool.id,
    visibility: tool.entity.visibility,
    publish: tool.published,
    name: tool.spec.name,
    description: tool.spec.description,
    transport: tool.spec.transport,
    connection_profile_ref: "default",
    tool_name: tool.spec.tool_name,
    input_schema: tool.spec.input_schema,
    output_schema: tool.spec.output_schema,
    safety_policy: tool.spec.safety_policy,
    offline_compatible: tool.spec.offline_compatible,
    inputSchemaText: stringifyJson(tool.spec.input_schema),
    outputSchemaText: stringifyJson(tool.spec.output_schema),
    safetyPolicyText: stringifyJson(tool.spec.safety_policy),
  };
}

export default function CatalogControlPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const { showErrorFeedback, showSuccessFeedback } = useActionFeedback();
  const [state, setState] = useState<LoadState>("idle");
  const [agents, setAgents] = useState<CatalogAgent[]>([]);
  const [tools, setTools] = useState<CatalogTool[]>([]);
  const [models, setModels] = useState<ModelCatalogItem[]>([]);
  const [agentForm, setAgentForm] = useState<AgentFormState>(DEFAULT_AGENT_FORM);
  const [toolForm, setToolForm] = useState<ToolFormState>(DEFAULT_TOOL_FORM);
  const [agentValidationResults, setAgentValidationResults] = useState<Record<string, CatalogAgentValidation>>({});
  const [toolValidationResults, setToolValidationResults] = useState<Record<string, CatalogToolValidation>>({});
  const [validatingAgentId, setValidatingAgentId] = useState("");
  const [validatingToolId, setValidatingToolId] = useState("");
  const [savingAgent, setSavingAgent] = useState(false);
  const [savingTool, setSavingTool] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  async function loadCatalogState(): Promise<void> {
    if (!token) {
      setState("error");
      setErrorMessage(t("catalogControl.feedback.authRequired"));
      return;
    }

    setState("loading");
    setErrorMessage("");

    try {
      const [agentsPayload, toolsPayload, modelsPayload] = await Promise.all([
        listCatalogAgents(token),
        listCatalogTools(token),
        listEnabledModels(token),
      ]);
      setAgents(agentsPayload);
      setTools(toolsPayload);
      setModels(modelsPayload);
      setState("success");
    } catch (error) {
      setState("error");
      setErrorMessage(error instanceof Error ? error.message : t("catalogControl.feedback.loadFailed"));
    }
  }

  useEffect(() => {
    void loadCatalogState();
  }, [token]);

  const publishedAgents = agents.filter((agent) => agent.published).length;
  const publishedTools = tools.filter((tool) => tool.published).length;

  async function handleAgentValidate(agentId: string): Promise<void> {
    if (!token) {
      return;
    }
    setValidatingAgentId(agentId);
    try {
      const result = await validateCatalogAgent(agentId, token);
      setAgentValidationResults((current) => ({ ...current, [agentId]: result }));
      showSuccessFeedback(t("catalogControl.feedback.agentValidated", { name: result.agent.spec.name }));
    } catch (error) {
      showErrorFeedback(error, t("catalogControl.feedback.validationFailed"));
    } finally {
      setValidatingAgentId("");
    }
  }

  async function handleToolValidate(toolId: string): Promise<void> {
    if (!token) {
      return;
    }
    setValidatingToolId(toolId);
    try {
      const result = await validateCatalogTool(toolId, token);
      setToolValidationResults((current) => ({ ...current, [toolId]: result }));
      showSuccessFeedback(t("catalogControl.feedback.toolValidated", { name: result.tool.spec.name }));
    } catch (error) {
      showErrorFeedback(error, t("catalogControl.feedback.validationFailed"));
    } finally {
      setValidatingToolId("");
    }
  }

  async function handleAgentSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token) {
      return;
    }
    setSavingAgent(true);
    try {
      const payload: CatalogAgentMutationInput = {
        id: agentForm.id || undefined,
        visibility: agentForm.visibility,
        publish: agentForm.publish,
        name: agentForm.name,
        description: agentForm.description,
        instructions: agentForm.instructions,
        default_model_ref: agentForm.default_model_ref?.trim() ? agentForm.default_model_ref.trim() : null,
        tool_refs: agentForm.tool_refs,
        runtime_constraints: agentForm.runtime_constraints,
      };
      const saved =
        agentForm.mode === "create"
          ? await createCatalogAgent(payload, token)
          : await updateCatalogAgent(agentForm.agentId, payload, token);
      setAgentForm(buildAgentForm(saved));
      await loadCatalogState();
      showSuccessFeedback(
        t(agentForm.mode === "create" ? "catalogControl.feedback.agentCreated" : "catalogControl.feedback.agentUpdated", {
          name: saved.spec.name,
        }),
      );
    } catch (error) {
      showErrorFeedback(error, t("catalogControl.feedback.saveFailed"));
    } finally {
      setSavingAgent(false);
    }
  }

  async function handleToolSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token) {
      return;
    }
    setSavingTool(true);
    try {
      const inputSchema = parseJsonObject(
        toolForm.inputSchemaText,
        t("catalogControl.feedback.invalidJson", { field: t("catalogControl.forms.tool.inputSchema") }),
      );
      const outputSchema = parseJsonObject(
        toolForm.outputSchemaText,
        t("catalogControl.feedback.invalidJson", { field: t("catalogControl.forms.tool.outputSchema") }),
      );
      const safetyPolicy = parseJsonObject(
        toolForm.safetyPolicyText,
        t("catalogControl.feedback.invalidJson", { field: t("catalogControl.forms.tool.safetyPolicy") }),
      );

      const payload: CatalogToolMutationInput = {
        id: toolForm.id || undefined,
        visibility: toolForm.visibility,
        publish: toolForm.publish,
        name: toolForm.name,
        description: toolForm.description,
        transport: toolForm.transport,
        connection_profile_ref: "default",
        tool_name: toolForm.tool_name,
        input_schema: inputSchema,
        output_schema: outputSchema,
        safety_policy: safetyPolicy,
        offline_compatible: toolForm.offline_compatible,
      };
      const saved =
        toolForm.mode === "create"
          ? await createCatalogTool(payload, token)
          : await updateCatalogTool(toolForm.toolId, payload, token);
      setToolForm(buildToolForm(saved));
      await loadCatalogState();
      showSuccessFeedback(
        t(toolForm.mode === "create" ? "catalogControl.feedback.toolCreated" : "catalogControl.feedback.toolUpdated", {
          name: saved.spec.name,
        }),
      );
    } catch (error) {
      showErrorFeedback(error, t("catalogControl.feedback.saveFailed"));
    } finally {
      setSavingTool(false);
    }
  }

  return (
    <section className="card-stack">
      <article className="panel card-stack">
        <div className="platform-section-header">
          <div className="status-row">
            <h2 className="section-title">{t("catalogControl.title")}</h2>
            <p className="status-text">{t("catalogControl.description")}</p>
          </div>
          <button type="button" className="btn btn-primary" onClick={() => void loadCatalogState()} disabled={state === "loading"}>
            {state === "loading" ? t("catalogControl.actions.refreshing") : t("catalogControl.actions.refresh")}
          </button>
        </div>

        <div className="platform-summary-grid">
          <div className="platform-summary-card">
            <span className="field-label">{t("catalogControl.summary.agents")}</span>
            <strong>{agents.length}</strong>
            <span className="status-text">{t("catalogControl.summary.publishedCount", { count: publishedAgents })}</span>
          </div>
          <div className="platform-summary-card">
            <span className="field-label">{t("catalogControl.summary.tools")}</span>
            <strong>{tools.length}</strong>
            <span className="status-text">{t("catalogControl.summary.publishedCount", { count: publishedTools })}</span>
          </div>
          <div className="platform-summary-card">
            <span className="field-label">{t("catalogControl.summary.models")}</span>
            <strong>{models.length}</strong>
            <span className="status-text">{t(`catalogControl.state.${state}`)}</span>
          </div>
        </div>
        {errorMessage ? <p className="status-text">{errorMessage}</p> : null}
      </article>

      <article className="panel card-stack">
        <div className="status-row">
          <h3 className="section-title">{t("catalogControl.sections.agents")}</h3>
          <p className="status-text">{t("catalogControl.agents.description")}</p>
        </div>

        <form className="card-stack" onSubmit={(event) => void handleAgentSubmit(event)}>
          <div className="form-grid">
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.forms.agent.id")}</span>
              <input
                className="field-input"
                value={agentForm.id}
                disabled={agentForm.mode === "edit"}
                onChange={(event) => setAgentForm((current) => ({ ...current, id: event.target.value }))}
              />
            </label>
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.forms.agent.name")}</span>
              <input className="field-input" value={agentForm.name} onChange={(event) => setAgentForm((current) => ({ ...current, name: event.target.value }))} />
            </label>
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.forms.agent.defaultModel")}</span>
              <select
                className="field-input"
                value={agentForm.default_model_ref ?? ""}
                onChange={(event) =>
                  setAgentForm((current) => ({
                    ...current,
                    default_model_ref: event.target.value || null,
                  }))
                }
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
                value={agentForm.publish ? "published" : "draft"}
                onChange={(event) => setAgentForm((current) => ({ ...current, publish: event.target.value === "published" }))}
              >
                <option value="draft">{t("catalogControl.badges.draft")}</option>
                <option value="published">{t("catalogControl.badges.published")}</option>
              </select>
            </label>
          </div>
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.agent.description")}</span>
            <textarea className="field-input quote-admin-textarea" value={agentForm.description} onChange={(event) => setAgentForm((current) => ({ ...current, description: event.target.value }))} />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.agent.instructions")}</span>
            <textarea className="field-input quote-admin-textarea" value={agentForm.instructions} onChange={(event) => setAgentForm((current) => ({ ...current, instructions: event.target.value }))} />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.agent.toolRefs")}</span>
            <select
              className="field-input catalog-multiselect"
              multiple
              value={agentForm.tool_refs}
              onChange={(event) =>
                setAgentForm((current) => ({
                  ...current,
                  tool_refs: Array.from(event.currentTarget.selectedOptions).map((option) => option.value),
                }))
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
                value={agentForm.runtime_constraints.internet_required ? "true" : "false"}
                onChange={(event) =>
                  setAgentForm((current) => ({
                    ...current,
                    runtime_constraints: {
                      ...current.runtime_constraints,
                      internet_required: event.target.value === "true",
                    },
                  }))
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
                value={agentForm.runtime_constraints.sandbox_required ? "true" : "false"}
                onChange={(event) =>
                  setAgentForm((current) => ({
                    ...current,
                    runtime_constraints: {
                      ...current.runtime_constraints,
                      sandbox_required: event.target.value === "true",
                    },
                  }))
                }
              >
                <option value="false">{t("catalogControl.badges.no")}</option>
                <option value="true">{t("catalogControl.badges.yes")}</option>
              </select>
            </label>
          </div>
          <div className="status-row">
            <button type="submit" className="btn btn-primary" disabled={savingAgent}>
              {savingAgent ? t("catalogControl.actions.saving") : t(agentForm.mode === "create" ? "catalogControl.actions.createAgent" : "catalogControl.actions.updateAgent")}
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => setAgentForm(DEFAULT_AGENT_FORM)}>
              {t("catalogControl.actions.newAgent")}
            </button>
          </div>
        </form>

        <div className="catalog-grid">
          {agents.map((agent) => {
            const validation = agentValidationResults[agent.id]?.validation;
            return (
              <article key={agent.id} className="platform-capability-card">
                <div className="platform-card-header">
                  <h4 className="section-title">{agent.spec.name}</h4>
                  <span className="platform-badge" data-tone={agent.published ? "active" : "required"}>
                    {agent.published ? t("catalogControl.badges.published") : t("catalogControl.badges.draft")}
                  </span>
                </div>
                <p className="status-text">{agent.spec.description}</p>
                <p className="status-text">
                  <code className="code-inline">{agent.id}</code>
                </p>
                <p className="status-text">{t("catalogControl.summary.version", { version: agent.current_version })}</p>
                <div className="status-row">
                  <button type="button" className="btn btn-secondary" onClick={() => setAgentForm(buildAgentForm(agent))}>
                    {t("catalogControl.actions.edit")}
                  </button>
                  <button type="button" className="btn btn-secondary" onClick={() => void handleAgentValidate(agent.id)} disabled={validatingAgentId === agent.id}>
                    {validatingAgentId === agent.id ? t("catalogControl.actions.validating") : t("catalogControl.actions.validate")}
                  </button>
                </div>
                {validation ? (
                  <div className="card-stack">
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

      <article className="panel card-stack">
        <div className="status-row">
          <h3 className="section-title">{t("catalogControl.sections.tools")}</h3>
          <p className="status-text">{t("catalogControl.tools.description")}</p>
        </div>

        <form className="card-stack" onSubmit={(event) => void handleToolSubmit(event)}>
          <div className="form-grid">
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.forms.tool.id")}</span>
              <input
                className="field-input"
                value={toolForm.id}
                disabled={toolForm.mode === "edit"}
                onChange={(event) => setToolForm((current) => ({ ...current, id: event.target.value }))}
              />
            </label>
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.forms.tool.name")}</span>
              <input className="field-input" value={toolForm.name} onChange={(event) => setToolForm((current) => ({ ...current, name: event.target.value }))} />
            </label>
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.forms.tool.transport")}</span>
              <select
                className="field-input"
                value={toolForm.transport}
                onChange={(event) => setToolForm((current) => ({ ...current, transport: event.target.value as "mcp" | "sandbox_http" }))}
              >
                <option value="mcp">{t("catalogControl.transport.mcp")}</option>
                <option value="sandbox_http">{t("catalogControl.transport.sandbox")}</option>
              </select>
            </label>
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.forms.status")}</span>
              <select
                className="field-input"
                value={toolForm.publish ? "published" : "draft"}
                onChange={(event) => setToolForm((current) => ({ ...current, publish: event.target.value === "published" }))}
              >
                <option value="draft">{t("catalogControl.badges.draft")}</option>
                <option value="published">{t("catalogControl.badges.published")}</option>
              </select>
            </label>
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.forms.tool.toolName")}</span>
              <input className="field-input" value={toolForm.tool_name} onChange={(event) => setToolForm((current) => ({ ...current, tool_name: event.target.value }))} />
            </label>
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.forms.tool.offlineCompatible")}</span>
              <select
                className="field-input"
                value={toolForm.offline_compatible ? "true" : "false"}
                onChange={(event) => setToolForm((current) => ({ ...current, offline_compatible: event.target.value === "true" }))}
              >
                <option value="false">{t("catalogControl.badges.no")}</option>
                <option value="true">{t("catalogControl.badges.yes")}</option>
              </select>
            </label>
          </div>
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.tool.description")}</span>
            <textarea className="field-input quote-admin-textarea" value={toolForm.description} onChange={(event) => setToolForm((current) => ({ ...current, description: event.target.value }))} />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.tool.inputSchema")}</span>
            <textarea className="field-input quote-admin-textarea" value={toolForm.inputSchemaText} onChange={(event) => setToolForm((current) => ({ ...current, inputSchemaText: event.target.value }))} />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.tool.outputSchema")}</span>
            <textarea className="field-input quote-admin-textarea" value={toolForm.outputSchemaText} onChange={(event) => setToolForm((current) => ({ ...current, outputSchemaText: event.target.value }))} />
          </label>
          <label className="card-stack">
            <span className="field-label">{t("catalogControl.forms.tool.safetyPolicy")}</span>
            <textarea className="field-input quote-admin-textarea" value={toolForm.safetyPolicyText} onChange={(event) => setToolForm((current) => ({ ...current, safetyPolicyText: event.target.value }))} />
          </label>
          <p className="status-text">{t("catalogControl.forms.tool.connectionProfile")}</p>
          <div className="status-row">
            <button type="submit" className="btn btn-primary" disabled={savingTool}>
              {savingTool ? t("catalogControl.actions.saving") : t(toolForm.mode === "create" ? "catalogControl.actions.createTool" : "catalogControl.actions.updateTool")}
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => setToolForm(DEFAULT_TOOL_FORM)}>
              {t("catalogControl.actions.newTool")}
            </button>
          </div>
        </form>

        <div className="catalog-grid">
          {tools.map((tool) => {
            const validation = toolValidationResults[tool.id]?.validation;
            return (
              <article key={tool.id} className="platform-capability-card">
                <div className="platform-card-header">
                  <h4 className="section-title">{tool.spec.name}</h4>
                  <span className="platform-badge" data-tone={tool.published ? "active" : "required"}>
                    {tool.published ? t("catalogControl.badges.published") : t("catalogControl.badges.draft")}
                  </span>
                </div>
                <p className="status-text">{tool.spec.description}</p>
                <p className="status-text">
                  <code className="code-inline">{tool.id}</code>
                </p>
                <p className="status-text">{t("catalogControl.tools.transportLabel", { transport: t(`catalogControl.transport.${tool.spec.transport === "mcp" ? "mcp" : "sandbox"}`) })}</p>
                <div className="status-row">
                  <button type="button" className="btn btn-secondary" onClick={() => setToolForm(buildToolForm(tool))}>
                    {t("catalogControl.actions.edit")}
                  </button>
                  <button type="button" className="btn btn-secondary" onClick={() => void handleToolValidate(tool.id)} disabled={validatingToolId === tool.id}>
                    {validatingToolId === tool.id ? t("catalogControl.actions.validating") : t("catalogControl.actions.validate")}
                  </button>
                </div>
                {validation ? (
                  <div className="card-stack">
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
    </section>
  );
}
