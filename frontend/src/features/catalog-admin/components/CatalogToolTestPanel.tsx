import { useTranslation } from "react-i18next";
import type { CatalogTool, CatalogToolTestResult } from "../../../api/catalog";
import type { ToolTestFormState } from "../hooks/useCatalogControl";

type CatalogToolTestPanelProps = {
  tool: CatalogTool | null;
  form: ToolTestFormState;
  testing: boolean;
  errorMessage: string;
  result: CatalogToolTestResult | null;
  onChange: (value: ToolTestFormState) => void;
  onSubmit: () => void;
};

function stringifyJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

export default function CatalogToolTestPanel({
  tool,
  form,
  testing,
  errorMessage,
  result,
  onChange,
  onSubmit,
}: CatalogToolTestPanelProps): JSX.Element {
  const { t } = useTranslation("common");

  if (!tool) {
    return (
      <article className="panel card-stack">
        <h3 className="section-title">{t("catalogControl.tools.testTitle")}</h3>
        <p className="status-text">{t("catalogControl.tools.testMissing")}</p>
      </article>
    );
  }

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <div className="card-stack">
          <h3 className="section-title">{t("catalogControl.tools.testTitle")}</h3>
          <p className="status-text">{t("catalogControl.tools.testDescription", { name: tool.spec.name })}</p>
        </div>
        <span className="platform-badge" data-tone={tool.spec.offline_compatible ? "enabled" : "required"}>
          {tool.spec.offline_compatible ? t("catalogControl.badges.yes") : t("catalogControl.badges.no")}
        </span>
      </div>

      <div className="card-stack">
        <span className="field-label">{t("catalogControl.tools.transportLabel", {
          transport: t(`catalogControl.transport.${tool.spec.transport === "mcp" ? "mcp" : "sandbox"}`),
        })}</span>
        <code className="code-inline">{tool.id}</code>
      </div>

      <label className="card-stack">
        <span className="field-label">{t("catalogControl.forms.toolTest.input")}</span>
        <textarea
          className="field-input form-textarea"
          rows={14}
          value={form.inputText}
          onChange={(event) => onChange({ ...form, inputText: event.target.value })}
        />
      </label>

      <div className="platform-action-row">
        <span className="status-text">
          {errorMessage || t("catalogControl.tools.testHelper")}
        </span>
        <div className="form-actions">
          <button type="button" className="btn btn-primary" onClick={onSubmit} disabled={testing}>
            {testing ? t("catalogControl.actions.testingTool") : t("catalogControl.actions.testTool")}
          </button>
        </div>
      </div>

      <div className="panel panel-nested card-stack">
        <span className="field-label">{t("catalogControl.tools.inputSchemaTitle")}</span>
        <pre className="code-block">{stringifyJson(tool.spec.input_schema)}</pre>
      </div>

      {result ? (
        <div className="panel panel-nested card-stack" data-testid="catalog-tool-test-result">
          <div className="status-row">
            <span className="field-label">{t("catalogControl.tools.testResultTitle")}</span>
            <span className="platform-badge" data-tone={result.execution.ok ? "enabled" : "required"}>
              {result.execution.ok ? t("catalogControl.validation.valid") : t("catalogControl.validation.invalid")}
            </span>
          </div>
          <p className="status-text">{t("catalogControl.tools.testStatus", { statusCode: result.execution.status_code })}</p>
          <div className="card-stack">
            <span className="field-label">{t("catalogControl.tools.requestTitle")}</span>
            <pre className="code-block">{stringifyJson(result.execution.input)}</pre>
          </div>
          <div className="card-stack">
            <span className="field-label">{t("catalogControl.tools.responseTitle")}</span>
            <pre className="code-block">{stringifyJson(result.execution.result)}</pre>
          </div>
        </div>
      ) : null}
    </article>
  );
}
