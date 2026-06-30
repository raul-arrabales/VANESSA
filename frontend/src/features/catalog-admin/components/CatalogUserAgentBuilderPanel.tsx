import type { FormEvent } from "react";
import { useMemo, useRef } from "react";
import { useTranslation } from "react-i18next";
import type { CatalogMcpServer } from "../../../api/catalog";
import type { WorkflowAction, WorkflowVariableDefinition } from "../../../api/agentProjects";
import type { ModelCatalogItem } from "../../../api/modelops";
import type { AgentProjectFormState } from "../userAgentProjectForm";

type Props = {
  form: AgentProjectFormState;
  saving: boolean;
  mcpServers: CatalogMcpServer[];
  models: ModelCatalogItem[];
  onChange: (value: AgentProjectFormState) => void;
  onAgentTypeChange: (agentType: AgentProjectFormState["agentType"]) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onReset: () => void;
};

type AvailableVariable = {
  name: string;
  label: string;
  type: string;
};

type EditableWorkflowVariable = WorkflowVariableDefinition & {
  path?: string;
};

type PromptVariableScope = {
  actionId: string;
  actionName: string;
  variables: AvailableVariable[];
};

const VARIABLE_NAME_PATTERN = /^[a-zA-Z_][a-zA-Z0-9_]*$/;
const SUPPORTED_WORKFLOW_VARIABLE_TYPES = new Set(["text"]);

export default function CatalogUserAgentBuilderPanel({
  form,
  saving,
  mcpServers,
  models,
  onChange,
  onAgentTypeChange,
  onSubmit,
  onReset,
}: Props): JSX.Element {
  const { t } = useTranslation("common");
  const instructionsDisabled = form.agentType === "workflow";
  const isTypeStepComplete = form.agentType === "workflow" && form.channelType === "vanessa_webapp" && form.interfaceType === "chat";
  const isBasicsStepComplete = isTypeStepComplete
    && Boolean(form.id.trim() && form.name.trim() && form.description.trim());
  const enabledMcpServers = useMemo(() => mcpServers.filter((server) => server.spec.enabled), [mcpServers]);
  const workflowComplete = isWorkflowComplete(form.workflowActions, enabledMcpServers);

  const updateAction = (index: number, action: WorkflowAction): void => {
    onChange({
      ...form,
      workflowActions: form.workflowActions.map((item, itemIndex) => (itemIndex === index ? action : item)),
    });
  };

  const removeAction = (index: number): void => {
    onChange({
      ...form,
      workflowActions: form.workflowActions.filter((_item, itemIndex) => itemIndex !== index),
    });
  };

  const appendAction = (type: WorkflowAction["type"]): void => {
    onChange({
      ...form,
      workflowActions: [...form.workflowActions, buildNewAction(type, form.workflowActions.length)],
    });
  };

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
              <select className="field-input" value={form.agentType} onChange={(event) => onAgentTypeChange(event.currentTarget.value as AgentProjectFormState["agentType"])}>
                <option value="">{t("catalogControl.agents.userProjects.selectAgentType")}</option>
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

        {isTypeStepComplete ? (
          <section className="panel panel-nested card-stack">
            <h4 className="section-title">{t("catalogControl.agents.userProjects.stepBasics")}</h4>
            <div className="form-grid">
              <label className="card-stack">
                <span className="field-label">{t("catalogControl.forms.agent.id")}</span>
                <input className="field-input" value={form.id} disabled />
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
              <textarea
                className="field-input form-textarea"
                value={instructionsDisabled ? t("catalogControl.agents.userProjects.workflowInstructionsDisabled") : form.instructions}
                onChange={(event) => onChange({ ...form, instructions: event.currentTarget.value })}
                disabled={instructionsDisabled}
              />
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
        ) : null}

        {isBasicsStepComplete ? (
          <section className="panel panel-nested card-stack">
            <h4 className="section-title">{t("catalogControl.agents.userProjects.stepWorkflow")}</h4>
            <p className="status-text">{t("catalogControl.agents.userProjects.workflowHelp")}</p>
            <div className="card-stack">
              {form.workflowActions.map((action, index) => (
                <WorkflowActionEditor
                  key={action.id}
                  action={action}
                  actionIndex={index}
                  enabledMcpServers={enabledMcpServers}
                  availableVariables={variablesBeforeAction(form.workflowActions, index)}
                  onChange={(updated) => updateAction(index, updated)}
                  onRemove={() => removeAction(index)}
                />
              ))}
            </div>
            {canAppendAction(form.workflowActions, enabledMcpServers) ? (
              <div className="status-row">
                <select
                  aria-label={t("catalogControl.agents.userProjects.addAction")}
                  className="field-input"
                  value=""
                  onChange={(event) => {
                    const value = event.currentTarget.value as WorkflowAction["type"];
                    if (value) appendAction(value);
                  }}
                >
                  <option value="">{t("catalogControl.agents.userProjects.addAction")}</option>
                  <option value="get_user_input">{t("catalogControl.agents.userProjects.actionGetInput")}</option>
                  <option value="mcp_tool">{t("catalogControl.agents.userProjects.actionMcpTool")}</option>
                  <option value="send_output">{t("catalogControl.agents.userProjects.actionSendOutput")}</option>
                </select>
              </div>
            ) : (
              <p className="status-text">{t("catalogControl.agents.userProjects.completeActionBeforeNext")}</p>
            )}
          </section>
        ) : null}

        {isBasicsStepComplete ? (
          <div className="status-row">
            <button type="submit" className="btn btn-primary" disabled={saving || !workflowComplete}>
              {saving ? t("catalogControl.actions.saving") : t("catalogControl.agents.userProjects.save")}
            </button>
          </div>
        ) : null}
      </form>
    </article>
  );
}

function WorkflowActionEditor({
  action,
  actionIndex,
  enabledMcpServers,
  availableVariables,
  onChange,
  onRemove,
}: {
  action: WorkflowAction;
  actionIndex: number;
  enabledMcpServers: CatalogMcpServer[];
  availableVariables: AvailableVariable[];
  onChange: (action: WorkflowAction) => void;
  onRemove: () => void;
}): JSX.Element {
  const { t } = useTranslation("common");
  const promptRef = useRef<HTMLTextAreaElement | null>(null);
  const selectedServer = action.type === "mcp_tool"
    ? enabledMcpServers.find((server) => server.spec.slug === action.mcp_server_slug) ?? null
    : null;
  const requiredInputs = selectedServer ? requiredSchemaFields(selectedServer.spec.input_schema) : [];
  const outputFields = selectedServer ? schemaPropertyNames(selectedServer.spec.output_schema) : [];
  const promptScopes: PromptVariableScope[] = action.type === "get_user_input"
    ? [{
      actionId: action.id,
      actionName: action.name,
      variables: action.variables
        .filter((variable) => VARIABLE_NAME_PATTERN.test(variable.name))
        .map((variable) => ({ name: variable.name, label: variable.label, type: variable.type })),
    }].filter((scope) => scope.variables.length > 0)
    : action.type === "mcp_tool"
      ? [{
        actionId: action.id,
        actionName: action.name,
        variables: availableVariables,
      }].filter((scope) => scope.variables.length > 0)
      : [{
        actionId: action.id,
        actionName: action.name,
        variables: availableVariables.filter((variable) => action.variable_refs.includes(variable.name)),
      }].filter((scope) => scope.variables.length > 0);

  const insertPromptVariable = (variableName: string): void => {
    const token = `{{${variableName}}}`;
    const textarea = promptRef.current;
    const selectionStart = textarea ? textarea.selectionStart : action.prompt.length;
    const selectionEnd = textarea ? textarea.selectionEnd : action.prompt.length;
    const { nextValue, cursorPosition } = insertTokenAtSelection(action.prompt, token, selectionStart, selectionEnd);
    onChange({ ...action, prompt: nextValue });
    window.requestAnimationFrame(() => {
      const target = promptRef.current;
      if (target) {
        target.focus();
        target.setSelectionRange(cursorPosition, cursorPosition);
      }
    });
  };

  return (
    <section className="panel panel-nested card-stack">
      <div className="status-row">
        <h5 className="section-title">{actionIndex + 1}. {actionLabel(action.type, t)}</h5>
        <button type="button" className="btn btn-secondary" onClick={onRemove}>{t("catalogControl.actions.remove")}</button>
      </div>
      <label className="card-stack">
        <span className="field-label">{t("catalogControl.agents.userProjects.actionName")}</span>
        <input className="field-input" value={action.name} onChange={(event) => onChange({ ...action, name: event.currentTarget.value })} />
      </label>
      {action.type === "get_user_input" ? (
        <>
          <WorkflowPromptEditor
            label={t("catalogControl.agents.userProjects.userInputPrompt")}
            value={action.prompt}
            scopes={promptScopes}
            emptyMessage={t("catalogControl.agents.userProjects.noInputVariables")}
            textareaRef={(node) => {
              promptRef.current = node;
            }}
            onChange={(value) => onChange({ ...action, prompt: value })}
            onInsertVariable={insertPromptVariable}
          />
          <div className="card-stack">
            <span className="field-label">{t("catalogControl.agents.userProjects.outputVariables")}</span>
            <WorkflowVariableListEditor
              variables={action.variables}
              mode="user-input"
              onChange={(variables) => onChange({ ...action, variables })}
            />
          </div>
        </>
      ) : null}
      {action.type === "mcp_tool" ? (
        <>
          <WorkflowPromptEditor
            label={t("catalogControl.agents.userProjects.workflowToolArgumentsPrompt")}
            value={action.prompt}
            scopes={promptScopes}
            emptyMessage={t("catalogControl.agents.userProjects.noToolVariables")}
            textareaRef={(node) => {
              promptRef.current = node;
            }}
            onChange={(value) => onChange({ ...action, prompt: value })}
            onInsertVariable={insertPromptVariable}
          />
          <div className="form-grid">
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.agents.userProjects.workflowMcp")}</span>
              <select className="field-input" value={action.mcp_server_slug} onChange={(event) => {
                const server = enabledMcpServers.find((item) => item.spec.slug === event.currentTarget.value);
                onChange({
                  ...action,
                  mcp_server_slug: event.currentTarget.value,
                  exposed_tool_name: server?.spec.exposed_tool_name ?? "",
                  name: action.name || server?.spec.name || "Invoke MCP tool",
                  input_bindings: {},
                  output_variables: action.output_variables.length
                    ? action.output_variables
                    : [{ name: "", label: "", type: "text", required: true }],
                });
              }}>
                <option value="">{t("catalogControl.agents.userProjects.selectMcp")}</option>
                {enabledMcpServers.map((server) => (
                  <option key={server.id} value={server.spec.slug}>{server.spec.name}</option>
                ))}
              </select>
            </label>
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.agents.userProjects.workflowTool")}</span>
              <input className="field-input" value={action.exposed_tool_name} onChange={(event) => onChange({ ...action, exposed_tool_name: event.currentTarget.value })} />
            </label>
          </div>
          {requiredInputs.length ? (
            <div className="card-stack">
              <span className="field-label">{t("catalogControl.agents.userProjects.requiredInputs")}</span>
              {requiredInputs.map((fieldName) => (
                <label className="card-stack" key={fieldName}>
                  <span className="status-text">{fieldName}</span>
                  <VariableSelect
                    label={fieldName}
                    value={action.input_bindings[fieldName]?.variable ?? ""}
                    variables={availableVariables}
                    onChange={(variable) => onChange({
                      ...action,
                      input_bindings: { ...action.input_bindings, [fieldName]: { variable } },
                    })}
                  />
                </label>
              ))}
            </div>
          ) : null}
          <div className="card-stack">
            <span className="field-label">{t("catalogControl.agents.userProjects.outputVariables")}</span>
            <WorkflowVariableListEditor
              variables={action.output_variables}
              mode="mcp-output"
              outputFields={outputFields}
              onChange={(output_variables) => onChange({ ...action, output_variables })}
            />
          </div>
        </>
      ) : null}
      {action.type === "send_output" ? (
        <>
          <WorkflowPromptEditor
            label={t("catalogControl.agents.userProjects.deliveryInstruction")}
            value={action.prompt}
            scopes={promptScopes}
            emptyMessage={t("catalogControl.agents.userProjects.noOutputVariables")}
            textareaRef={(node) => {
              promptRef.current = node;
            }}
            onChange={(value) => onChange({ ...action, prompt: value })}
            onInsertVariable={insertPromptVariable}
          />
          <div className="card-stack">
            <span className="field-label">{t("catalogControl.agents.userProjects.variablesToSend")}</span>
            {availableVariables.map((variable) => (
              <label className="status-row" key={variable.name}>
                <input
                  type="checkbox"
                  checked={action.variable_refs.includes(variable.name)}
                  onChange={(event) => onChange({
                    ...action,
                    variable_refs: event.currentTarget.checked
                      ? [...action.variable_refs, variable.name]
                      : action.variable_refs.filter((item) => item !== variable.name),
                  })}
                />
                <span>{variable.label || variable.name}</span>
              </label>
            ))}
          </div>
        </>
      ) : null}
    </section>
  );
}

function WorkflowVariableListEditor({
  variables,
  mode,
  outputFields = [],
  onChange,
}: {
  variables: EditableWorkflowVariable[];
  mode: "user-input" | "mcp-output";
  outputFields?: string[];
  onChange: (variables: EditableWorkflowVariable[]) => void;
}): JSX.Element {
  const { t } = useTranslation("common");
  const includeGuidance = mode === "user-input";
  const includePath = mode === "mcp-output";
  const updateVariable = (index: number, patch: Partial<EditableWorkflowVariable>): void => {
    onChange(variables.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item));
  };

  return (
    <>
      {variables.map((variable, variableIndex) => (
        <div className="form-grid" key={`${mode}-variable-${variableIndex}`}>
          <input
            aria-label={t("catalogControl.agents.userProjects.variableName")}
            className="field-input"
            placeholder={mode === "user-input" ? "user_name" : "tool_result"}
            value={variable.name}
            onChange={(event) => updateVariable(variableIndex, { name: event.currentTarget.value })}
          />
          <input
            aria-label={t("catalogControl.agents.userProjects.variableLabel")}
            className="field-input"
            placeholder={mode === "user-input" ? "User name" : "Tool result"}
            value={variable.label}
            onChange={(event) => updateVariable(variableIndex, { label: event.currentTarget.value })}
          />
          {includeGuidance ? (
            <input
              aria-label={t("catalogControl.agents.userProjects.variableGuidance")}
              className="field-input"
              placeholder="Ask for the user's name"
              value={variable.guidance ?? ""}
              onChange={(event) => updateVariable(variableIndex, { guidance: event.currentTarget.value })}
            />
          ) : null}
          {includePath ? (
            <select
              aria-label={t("catalogControl.agents.userProjects.outputPath")}
              className="field-input"
              value={variable.path ?? ""}
              onChange={(event) => updateVariable(variableIndex, { path: event.currentTarget.value })}
            >
              <option value="">{t("catalogControl.agents.userProjects.outputWholeResult")}</option>
              {outputFields.map((fieldName) => <option key={fieldName} value={fieldName}>{fieldName}</option>)}
            </select>
          ) : null}
        </div>
      ))}
      <button
        type="button"
        className="btn btn-secondary"
        onClick={() => onChange([...variables, { name: "", label: "", type: "text", required: true }])}
      >
        {t("catalogControl.agents.userProjects.addVariable")}
      </button>
    </>
  );
}

function WorkflowPromptEditor({
  label,
  value,
  scopes,
  emptyMessage,
  textareaRef,
  onChange,
  onInsertVariable,
}: {
  label: string;
  value: string;
  scopes: PromptVariableScope[];
  emptyMessage: string;
  textareaRef: (node: HTMLTextAreaElement | null) => void;
  onChange: (value: string) => void;
  onInsertVariable: (variableName: string) => void;
}): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <div className="card-stack">
      <label className="card-stack">
        <span className="field-label">{label}</span>
        <textarea
          ref={textareaRef}
          className="field-input form-textarea"
          value={value}
          onChange={(event) => onChange(event.currentTarget.value)}
        />
      </label>
      <div className="card-stack">
        <span className="field-label">{t("catalogControl.agents.userProjects.promptVariablesTitle")}</span>
        {scopes.length ? (
          scopes.map((scope) => (
            <div className="panel panel-nested card-stack" key={scope.actionId}>
              <span className="status-text">{scope.actionName}</span>
              <div className="status-row" style={{ flexWrap: "wrap", gap: "0.5rem" }}>
                {scope.variables.map((variable) => (
                  <button
                    key={`${scope.actionId}-${variable.name}`}
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => onInsertVariable(variable.name)}
                    aria-label={`${t("catalogControl.agents.userProjects.insertVariableToken")} ${variable.name}`}
                  >
                    {`{{${variable.name}}}`} ({variable.type})
                  </button>
                ))}
              </div>
            </div>
          ))
        ) : (
          <p className="status-text">{emptyMessage}</p>
        )}
      </div>
    </div>
  );
}

function VariableSelect({ label, value, variables, onChange }: { label: string; value: string; variables: AvailableVariable[]; onChange: (value: string) => void }): JSX.Element {
  const { t } = useTranslation("common");
  return (
    <select aria-label={label} className="field-input" value={value} onChange={(event) => onChange(event.currentTarget.value)}>
      <option value="">{t("catalogControl.agents.userProjects.selectVariable")}</option>
      {variables.map((variable) => <option key={variable.name} value={variable.name}>{variable.label || variable.name}</option>)}
    </select>
  );
}

function buildNewAction(type: WorkflowAction["type"], index: number): WorkflowAction {
  if (type === "get_user_input") {
    return {
      id: `get_user_input_${index + 1}`,
      type,
      name: "Collect user input",
      prompt: "Ask the user for the required information.",
      variables: [{ name: "", label: "", type: "text", required: true }],
    };
  }
  if (type === "mcp_tool") {
    return {
      id: `mcp_tool_${index + 1}`,
      type,
      name: "Invoke MCP tool",
      mcp_server_slug: "",
      exposed_tool_name: "",
      prompt: "Use the available workflow variables to compose valid tool arguments and capture the declared outputs.",
      input_bindings: {},
      output_variables: [{ name: "", label: "", type: "text", required: true }],
    };
  }
  return {
    id: `send_output_${index + 1}`,
    type,
    name: "Send output",
    prompt: "Compose a concise chat response for the user using the selected workflow variables.",
    variable_refs: [],
  };
}

function variablesBeforeAction(actions: WorkflowAction[], actionIndex: number): AvailableVariable[] {
  const variables: AvailableVariable[] = [];
  for (const action of actions.slice(0, actionIndex)) {
    if (action.type === "get_user_input") {
      variables.push(...action.variables.map((variable) => ({ name: variable.name, label: variable.label, type: variable.type })));
    }
    if (action.type === "mcp_tool") {
      variables.push(...action.output_variables.map((variable) => ({ name: variable.name, label: variable.label, type: variable.type })));
    }
  }
  return variables.filter((variable) => VARIABLE_NAME_PATTERN.test(variable.name));
}

function insertTokenAtSelection(
  value: string,
  token: string,
  selectionStart: number,
  selectionEnd: number,
): { nextValue: string; cursorPosition: number } {
  const before = value.slice(0, selectionStart);
  const after = value.slice(selectionEnd);
  const prefix = before && !/\s$/.test(before) ? " " : "";
  const suffix = after && !/^\s/.test(after) ? " " : "";
  const insertion = `${prefix}${token}${suffix}`;
  const nextValue = `${before}${insertion}${after}`;
  return {
    nextValue,
    cursorPosition: before.length + insertion.length,
  };
}

function actionProducesValidVariables(action: WorkflowAction): boolean {
  const variables = action.type === "get_user_input" ? action.variables : action.type === "mcp_tool" ? action.output_variables : [];
  return variables.length > 0 && variables.every((variable) => VARIABLE_NAME_PATTERN.test(variable.name) && variable.label.trim() && SUPPORTED_WORKFLOW_VARIABLE_TYPES.has(variable.type));
}

function isActionComplete(action: WorkflowAction, actionIndex: number, actions: WorkflowAction[], enabledMcpServers: CatalogMcpServer[]): boolean {
  if (!action.name.trim()) return false;
  if (action.type === "get_user_input") {
    return action.prompt.trim().length > 0 && actionProducesValidVariables(action);
  }
  if (action.type === "mcp_tool") {
    const server = enabledMcpServers.find((item) => item.spec.slug === action.mcp_server_slug);
    if (!server || !action.exposed_tool_name.trim() || !action.prompt.trim() || !actionProducesValidVariables(action)) return false;
    const available = new Set(variablesBeforeAction(actions, actionIndex).map((variable) => variable.name));
    return requiredSchemaFields(server.spec.input_schema).every((field) => available.has(action.input_bindings[field]?.variable ?? ""));
  }
  return action.prompt.trim().length > 0
    && action.variable_refs.length > 0
    && action.variable_refs.every((variable) => variablesBeforeAction(actions, actionIndex).some((item) => item.name === variable));
}

function canAppendAction(actions: WorkflowAction[], enabledMcpServers: CatalogMcpServer[]): boolean {
  if (!actions.length) return true;
  const lastIndex = actions.length - 1;
  return isActionComplete(actions[lastIndex], lastIndex, actions, enabledMcpServers) && actions[lastIndex].type !== "send_output";
}

function isWorkflowComplete(actions: WorkflowAction[], enabledMcpServers: CatalogMcpServer[]): boolean {
  return actions.length > 0
    && actions[0].type === "get_user_input"
    && actions[actions.length - 1].type === "send_output"
    && actions.every((action, index) => isActionComplete(action, index, actions, enabledMcpServers));
}

function requiredSchemaFields(schema: unknown): string[] {
  if (!schema || typeof schema !== "object" || Array.isArray(schema)) return [];
  const required = (schema as { required?: unknown }).required;
  return Array.isArray(required) ? required.map((item) => String(item)).filter(Boolean) : [];
}

function schemaPropertyNames(schema: unknown): string[] {
  if (!schema || typeof schema !== "object" || Array.isArray(schema)) return [];
  const properties = (schema as { properties?: unknown }).properties;
  if (!properties || typeof properties !== "object" || Array.isArray(properties)) return [];
  return Object.keys(properties);
}

function actionLabel(type: WorkflowAction["type"], t: (key: string) => string): string {
  if (type === "get_user_input") return t("catalogControl.agents.userProjects.actionGetInput");
  if (type === "mcp_tool") return t("catalogControl.agents.userProjects.actionMcpTool");
  return t("catalogControl.agents.userProjects.actionSendOutput");
}
