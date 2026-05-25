import type { RefObject } from "react";
import { useTranslation } from "react-i18next";
import type { CatalogToolTestResult } from "../../../api/catalog";
import { executionTraceEntries } from "../catalogExecutionTrace";
import CatalogRuntimeLog from "./CatalogRuntimeLog";

type CatalogToolTestResultProps = {
  result: CatalogToolTestResult;
  resultRef?: RefObject<HTMLDivElement>;
};

type ImagePayload = {
  data_base64: string;
  mime_type: string;
};

function stringifyJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

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

function CatalogToolResultImage({ src, title, alt }: { src: string; title: string; alt: string }): JSX.Element {
  return (
    <div className="card-stack">
      <span className="field-label">{title}</span>
      <div className="catalog-tool-result-image-frame">
        <img src={src} alt={alt} />
      </div>
    </div>
  );
}

function CatalogToolPayloadBlock({ title, value }: { title: string; value: unknown }): JSX.Element {
  return (
    <div className="card-stack">
      <span className="field-label">{title}</span>
      <pre className="code-block">{stringifyJson(value)}</pre>
    </div>
  );
}

export default function CatalogToolTestResultPanel({ result, resultRef }: CatalogToolTestResultProps): JSX.Element {
  const { t } = useTranslation("common");
  const resultImage = imagePayloadFromResult(result.execution.result);
  const resultImageSrc = resultImage ? `data:${resultImage.mime_type};base64,${resultImage.data_base64}` : "";
  const runtimeLogs = executionTraceEntries(result.execution.runtime_log);

  return (
    <div ref={resultRef} className="panel panel-nested card-stack" data-testid="catalog-tool-test-result">
      <div className="status-row">
        <span className="field-label">{t("catalogControl.tools.testResultTitle")}</span>
        <span className="platform-badge" data-tone={result.execution.ok ? "enabled" : "required"}>
          {result.execution.ok ? t("catalogControl.validation.valid") : t("catalogControl.validation.invalid")}
        </span>
      </div>
      <p className="status-text">{t("catalogControl.tools.testStatus", { statusCode: result.execution.status_code })}</p>
      {typeof result.execution.duration_ms === "number" ? (
        <p className="status-text">{t("catalogControl.tools.duration", { milliseconds: result.execution.duration_ms })}</p>
      ) : null}
      {resultImageSrc ? (
        <CatalogToolResultImage
          src={resultImageSrc}
          title={t("catalogControl.tools.resultImageTitle")}
          alt={t("catalogControl.tools.resultImageAlt")}
        />
      ) : null}
      <CatalogToolPayloadBlock title={t("catalogControl.tools.requestTitle")} value={result.execution.input} />
      <CatalogToolPayloadBlock title={t("catalogControl.tools.responseTitle")} value={result.execution.result} />
      <CatalogRuntimeLog entries={runtimeLogs} />
    </div>
  );
}
