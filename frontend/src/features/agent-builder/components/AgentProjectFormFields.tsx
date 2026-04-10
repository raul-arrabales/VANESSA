import type { Dispatch, SetStateAction } from "react";
import { useTranslation } from "react-i18next";
import type { AgentProjectFormState } from "../types";

type Props = {
  form: AgentProjectFormState;
  setForm: Dispatch<SetStateAction<AgentProjectFormState>>;
  disableId?: boolean;
};

export function AgentProjectFormFields({ form, setForm, disableId = false }: Props): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <>
      <label className="card-stack">
        <span className="field-label">{t("agentBuilder.fields.id")}</span>
        <input
          className="field-input"
          value={form.id}
          disabled={disableId}
          onChange={(event) => {
            const value = event.currentTarget.value;
            setForm((current) => ({ ...current, id: value }));
          }}
        />
      </label>
      <label className="card-stack">
        <span className="field-label">{t("agentBuilder.fields.visibility")}</span>
        <select
          className="field-input"
          value={form.visibility}
          onChange={(event) => {
            const value = event.currentTarget.value as AgentProjectFormState["visibility"];
            setForm((current) => ({ ...current, visibility: value }));
          }}
        >
          <option value="private">private</option>
          <option value="unlisted">unlisted</option>
          <option value="public">public</option>
        </select>
      </label>
      <label className="card-stack">
        <span className="field-label">{t("agentBuilder.fields.name")}</span>
        <input className="field-input" value={form.name} onChange={(event) => {
          const value = event.currentTarget.value;
          setForm((current) => ({ ...current, name: value }));
        }} />
      </label>
      <label className="card-stack">
        <span className="field-label">{t("agentBuilder.fields.description")}</span>
        <textarea className="field-input form-textarea" value={form.description} onChange={(event) => {
          const value = event.currentTarget.value;
          setForm((current) => ({ ...current, description: value }));
        }} />
      </label>
      <label className="card-stack">
        <span className="field-label">{t("agentBuilder.fields.instructions")}</span>
        <textarea className="field-input form-textarea" value={form.instructions} onChange={(event) => {
          const value = event.currentTarget.value;
          setForm((current) => ({ ...current, instructions: value }));
        }} />
      </label>
      <label className="card-stack">
        <span className="field-label">{t("agentBuilder.fields.defaultModelRef")}</span>
        <input className="field-input" value={form.defaultModelRef} onChange={(event) => {
          const value = event.currentTarget.value;
          setForm((current) => ({ ...current, defaultModelRef: value }));
        }} />
      </label>
      <label className="card-stack">
        <span className="field-label">{t("agentBuilder.fields.toolRefs")}</span>
        <textarea className="field-input form-textarea" value={form.toolRefsText} onChange={(event) => {
          const value = event.currentTarget.value;
          setForm((current) => ({ ...current, toolRefsText: value }));
        }} />
      </label>
      <label className="card-stack">
        <span className="field-label">{t("agentBuilder.fields.workflowDefinition")}</span>
        <textarea className="field-input form-textarea" value={form.workflowDefinitionText} onChange={(event) => {
          const value = event.currentTarget.value;
          setForm((current) => ({ ...current, workflowDefinitionText: value }));
        }} />
      </label>
      <label className="card-stack">
        <span className="field-label">{t("agentBuilder.fields.toolPolicy")}</span>
        <textarea className="field-input form-textarea" value={form.toolPolicyText} onChange={(event) => {
          const value = event.currentTarget.value;
          setForm((current) => ({ ...current, toolPolicyText: value }));
        }} />
      </label>
      <label className="status-row">
        <input type="checkbox" checked={form.internetRequired} onChange={(event) => {
          const value = event.currentTarget.checked;
          setForm((current) => ({ ...current, internetRequired: value }));
        }} />
        <span className="field-label">{t("agentBuilder.fields.internetRequired")}</span>
      </label>
      <label className="status-row">
        <input type="checkbox" checked={form.sandboxRequired} onChange={(event) => {
          const value = event.currentTarget.checked;
          setForm((current) => ({ ...current, sandboxRequired: value }));
        }} />
        <span className="field-label">{t("agentBuilder.fields.sandboxRequired")}</span>
      </label>
    </>
  );
}
