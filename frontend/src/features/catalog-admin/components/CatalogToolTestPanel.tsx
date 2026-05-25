import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import type { CatalogTool, CatalogToolTestResult } from "../../../api/catalog";
import { catalogToolBackendLabelKey } from "../catalogToolBackends";
import { applyImageFileToToolTestInput } from "../catalogToolTestInput";
import { useCatalogToolTestProgress } from "../hooks/useCatalogToolTestProgress";
import type { ToolTestFormState } from "../hooks/useCatalogToolTesting";
import CatalogToolTestProgressDialog, { catalogToolTestProgressStageCount } from "./CatalogToolTestProgressDialog";
import CatalogToolTestResultPanel from "./CatalogToolTestResult";

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
  const resultRef = useRef<HTMLDivElement>(null);
  const supportsImageUpload = tool?.spec.execution_backend === "image_analysis";
  const supportsPlateLogoUploads = tool?.id === "tool.image_plate_logo_replacement";
  const progress = useCatalogToolTestProgress({
    testing,
    traceEntries: result?.execution.runtime_log ?? [],
    stageCount: catalogToolTestProgressStageCount(),
  });

  useEffect(() => {
    if (!result || testing) {
      return;
    }
    if (typeof resultRef.current?.scrollIntoView === "function") {
      resultRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [result, testing]);

  const handleImageUpload = async (fieldName: "image" | "car_image" | "logo_image", file: File | undefined): Promise<void> => {
    if (!file) {
      return;
    }
    const inputText = await applyImageFileToToolTestInput(form.inputText, fieldName, file);
    onChange({ ...form, inputText });
  };

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
      {testing && progress.isProgressModalOpen ? (
        <CatalogToolTestProgressDialog
          tool={tool}
          elapsedMs={progress.elapsedMs}
          activeStageIndex={progress.activeStageIndex}
          progressPercent={progress.progressPercent}
          onDismiss={progress.dismissProgressModal}
        />
      ) : null}
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
        <span className="field-label">{t("catalogControl.tools.backendLabel", {
          backend: t(`catalogControl.executionBackend.${catalogToolBackendLabelKey(tool.spec.execution_backend)}`),
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

      {supportsImageUpload ? (
        <label className="card-stack">
          <span className="field-label">{t("catalogControl.forms.toolTest.imageUpload")}</span>
          <input
            className="field-input"
            type="file"
            accept="image/*"
            aria-label={t("catalogControl.forms.toolTest.imageUpload")}
            onChange={(event) => void handleImageUpload("image", event.currentTarget.files?.[0])}
          />
          <span className="status-text">{t("catalogControl.tools.imageUploadHelper")}</span>
        </label>
      ) : null}

      {supportsPlateLogoUploads ? (
        <div className="panel panel-nested card-stack">
          <span className="field-label">{t("catalogControl.forms.toolTest.plateLogoUploads")}</span>
          <div className="catalog-tool-upload-grid">
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.forms.toolTest.carImageUpload")}</span>
              <input
                className="field-input"
                type="file"
                accept="image/*"
                aria-label={t("catalogControl.forms.toolTest.carImageUpload")}
                onChange={(event) => void handleImageUpload("car_image", event.currentTarget.files?.[0])}
              />
            </label>
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.forms.toolTest.logoImageUpload")}</span>
              <input
                className="field-input"
                type="file"
                accept="image/*"
                aria-label={t("catalogControl.forms.toolTest.logoImageUpload")}
                onChange={(event) => void handleImageUpload("logo_image", event.currentTarget.files?.[0])}
              />
            </label>
          </div>
          <span className="status-text">{t("catalogControl.tools.plateLogoUploadHelper")}</span>
        </div>
      ) : null}

      <div className="platform-action-row">
        <span className="status-text">
          {errorMessage || t("catalogControl.tools.testHelper")}
        </span>
        <div className="form-actions">
          {testing && !progress.isProgressModalOpen ? (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={progress.openProgressModal}
            >
              {t("catalogControl.tools.progress.reopen")}
            </button>
          ) : null}
          <button type="button" className="btn btn-primary" onClick={onSubmit} disabled={testing}>
            {testing ? t("catalogControl.actions.testingTool") : t("catalogControl.actions.testTool")}
          </button>
        </div>
      </div>

      <div className="panel panel-nested card-stack">
        <span className="field-label">{t("catalogControl.tools.inputSchemaTitle")}</span>
        <pre className="code-block">{stringifyJson(tool.spec.input_schema)}</pre>
      </div>

      {result ? <CatalogToolTestResultPanel result={result} resultRef={resultRef} /> : null}
    </article>
  );
}
