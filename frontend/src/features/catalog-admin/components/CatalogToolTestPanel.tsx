import { useTranslation } from "react-i18next";
import type { CatalogTool, CatalogToolTestResult } from "../../../api/catalog";
import { catalogToolBackendLabelKey } from "../catalogToolBackends";
import type { ToolTestFormState } from "../hooks/useCatalogToolTesting";

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

function parseCurrentInput(text: string): Record<string, unknown> {
  try {
    const parsed = JSON.parse(text);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed as Record<string, unknown> : {};
  } catch {
    return {};
  }
}

function readImageFileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = typeof reader.result === "string" ? reader.result : "";
      const commaIndex = result.indexOf(",");
      resolve(commaIndex >= 0 ? result.slice(commaIndex + 1) : result);
    };
    reader.onerror = () => reject(reader.error ?? new Error("Unable to read image file."));
    reader.readAsDataURL(file);
  });
}

type ImagePayload = {
  data_base64: string;
  mime_type: string;
};

function imagePayloadFromResult(value: unknown): ImagePayload | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  const resultObject = value as Record<string, unknown>;
  const image = resultObject.image;
  if (!image || typeof image !== "object" || Array.isArray(image)) {
    return null;
  }
  const imageObject = image as Record<string, unknown>;
  const dataBase64 = typeof imageObject.data_base64 === "string" ? imageObject.data_base64.trim() : "";
  const mimeType = typeof imageObject.mime_type === "string" ? imageObject.mime_type.trim() : "";
  if (!dataBase64 || !mimeType) {
    return null;
  }
  return { data_base64: dataBase64, mime_type: mimeType };
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
  const supportsImageUpload = tool?.spec.execution_backend === "image_analysis";
  const supportsPlateLogoUploads = tool?.id === "tool.image_plate_logo_replacement";
  const resultImage = imagePayloadFromResult(result?.execution.result);
  const resultImageSrc = resultImage ? `data:${resultImage.mime_type};base64,${resultImage.data_base64}` : "";

  const handleImageUpload = async (file: File | undefined): Promise<void> => {
    if (!file) {
      return;
    }
    const dataBase64 = await readImageFileAsBase64(file);
    const input = parseCurrentInput(form.inputText);
    const nextInput = {
      ...input,
      image: {
        data_base64: dataBase64,
        mime_type: file.type || "application/octet-stream",
      },
    };
    onChange({ ...form, inputText: stringifyJson(nextInput) });
  };

  const handleNamedImageUpload = async (fieldName: "car_image" | "logo_image", file: File | undefined): Promise<void> => {
    if (!file) {
      return;
    }
    const dataBase64 = await readImageFileAsBase64(file);
    const input = parseCurrentInput(form.inputText);
    const nextInput = {
      ...input,
      [fieldName]: {
        data_base64: dataBase64,
        mime_type: file.type || "application/octet-stream",
      },
    };
    onChange({ ...form, inputText: stringifyJson(nextInput) });
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
            onChange={(event) => void handleImageUpload(event.currentTarget.files?.[0])}
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
                onChange={(event) => void handleNamedImageUpload("car_image", event.currentTarget.files?.[0])}
              />
            </label>
            <label className="card-stack">
              <span className="field-label">{t("catalogControl.forms.toolTest.logoImageUpload")}</span>
              <input
                className="field-input"
                type="file"
                accept="image/*"
                aria-label={t("catalogControl.forms.toolTest.logoImageUpload")}
                onChange={(event) => void handleNamedImageUpload("logo_image", event.currentTarget.files?.[0])}
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
          {resultImageSrc ? (
            <div className="card-stack">
              <span className="field-label">{t("catalogControl.tools.resultImageTitle")}</span>
              <div className="catalog-tool-result-image-frame">
                <img src={resultImageSrc} alt={t("catalogControl.tools.resultImageAlt")} />
              </div>
            </div>
          ) : null}
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
