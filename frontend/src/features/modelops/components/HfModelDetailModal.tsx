import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import ModalDialog from "../../../components/ModalDialog";
import type { HfModelDetails, HfModelFileDetails } from "../../../api/modelops/types";

type HfModelDetailModalProps = {
  model: HfModelDetails;
  onClose: () => void;
};

function formatOptionalValue(value: unknown, emptyLabel: string): string {
  if (value === null || value === undefined || value === "") {
    return emptyLabel;
  }
  if (typeof value === "boolean") {
    return value ? "yes" : "no";
  }
  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : emptyLabel;
  }
  return String(value);
}

function formatBytes(value: number | null | undefined, emptyLabel: string): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return emptyLabel;
  }
  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits: value >= 1024 * 1024 ? 1 : 0,
    notation: value >= 1024 * 1024 * 1024 ? "compact" : "standard",
  }).format(value);
}

function jsonBlock(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function getFileFormatSummary(files: HfModelFileDetails[]): Array<{ type: string; count: number }> {
  const counts = new Map<string, number>();
  files.forEach((file) => {
    const type = file.file_type || "unknown";
    counts.set(type, (counts.get(type) ?? 0) + 1);
  });
  return [...counts.entries()]
    .map(([type, count]) => ({ type, count }))
    .sort((left, right) => left.type.localeCompare(right.type));
}

export default function HfModelDetailModal({
  model,
  onClose,
}: HfModelDetailModalProps): JSX.Element {
  const { t } = useTranslation("common");
  const emptyLabel = t("modelOps.local.hfDetails.unavailable");
  const formatSummary = useMemo(() => getFileFormatSummary(model.files), [model.files]);
  const metadataSections = [
    { key: "card_data", label: t("modelOps.local.hfDetails.cardData"), value: model.card_data },
    { key: "config", label: t("modelOps.local.hfDetails.config"), value: model.config },
    { key: "safetensors", label: t("modelOps.local.hfDetails.safetensors"), value: model.safetensors },
    { key: "model_index", label: t("modelOps.local.hfDetails.modelIndex"), value: model.model_index },
    { key: "transformers_info", label: t("modelOps.local.hfDetails.transformersInfo"), value: model.transformers_info },
  ].filter((section) => section.value !== null && section.value !== undefined);

  return (
    <ModalDialog
      className="modelops-hf-detail-modal"
      eyebrow={t("modelOps.local.hfDetails.eyebrow")}
      title={model.source_id}
      description={t("modelOps.local.hfDetails.description")}
      onClose={onClose}
      actions={(
        <button type="button" className="btn btn-secondary" onClick={onClose}>
          {t("actionFeedback.dialog.close")}
        </button>
      )}
    >
      <div className="card-stack">
        <dl className="modelops-detail-grid">
          <div>
            <dt>{t("modelOps.local.hfDetails.name")}</dt>
            <dd>{formatOptionalValue(model.name, emptyLabel)}</dd>
          </div>
          <div>
            <dt>{t("modelOps.local.hfDetails.author")}</dt>
            <dd>{formatOptionalValue(model.author, emptyLabel)}</dd>
          </div>
          <div>
            <dt>{t("modelOps.local.hfDetails.pipeline")}</dt>
            <dd>{formatOptionalValue(model.pipeline_tag, emptyLabel)}</dd>
          </div>
          <div>
            <dt>{t("modelOps.local.hfDetails.library")}</dt>
            <dd>{formatOptionalValue(model.library_name, emptyLabel)}</dd>
          </div>
          <div>
            <dt>{t("modelOps.local.hfDetails.downloads")}</dt>
            <dd>{formatOptionalValue(model.downloads, emptyLabel)}</dd>
          </div>
          <div>
            <dt>{t("modelOps.local.hfDetails.likes")}</dt>
            <dd>{formatOptionalValue(model.likes, emptyLabel)}</dd>
          </div>
          <div>
            <dt>{t("modelOps.local.hfDetails.sha")}</dt>
            <dd>{formatOptionalValue(model.sha, emptyLabel)}</dd>
          </div>
          <div>
            <dt>{t("modelOps.local.hfDetails.gated")}</dt>
            <dd>{formatOptionalValue(model.gated, emptyLabel)}</dd>
          </div>
          <div>
            <dt>{t("modelOps.local.hfDetails.private")}</dt>
            <dd>{formatOptionalValue(model.private, emptyLabel)}</dd>
          </div>
          <div>
            <dt>{t("modelOps.local.hfDetails.disabled")}</dt>
            <dd>{formatOptionalValue(model.disabled, emptyLabel)}</dd>
          </div>
          <div>
            <dt>{t("modelOps.local.hfDetails.usedStorage")}</dt>
            <dd>{formatBytes(model.used_storage, emptyLabel)}</dd>
          </div>
          <div>
            <dt>{t("modelOps.local.hfDetails.lastModified")}</dt>
            <dd>{formatOptionalValue(model.last_modified, emptyLabel)}</dd>
          </div>
        </dl>

        <section className="card-stack">
          <h3 className="section-title">{t("modelOps.local.hfDetails.tags")}</h3>
          {model.tags.length ? (
            <div className="button-row">
              {model.tags.map((tag) => (
                <span key={tag} className="status-chip status-chip-neutral">{tag}</span>
              ))}
            </div>
          ) : (
            <p className="status-text">{emptyLabel}</p>
          )}
        </section>

        <section className="card-stack">
          <h3 className="section-title">{t("modelOps.local.hfDetails.fileFormats")}</h3>
          {formatSummary.length ? (
            <div className="button-row">
              {formatSummary.map((entry) => (
                <span key={entry.type} className="status-chip status-chip-neutral">
                  {t("modelOps.local.hfDetails.formatCount", { type: entry.type, count: entry.count })}
                </span>
              ))}
            </div>
          ) : (
            <p className="status-text">{emptyLabel}</p>
          )}
        </section>

        <section className="card-stack">
          <h3 className="section-title">{t("modelOps.local.hfDetails.files")}</h3>
          {model.files.length ? (
            <ul className="card-stack">
              {model.files.map((file) => (
                <li key={file.path} className="panel panel-nested card-stack">
                  <strong>{file.path}</strong>
                  <span className="status-text">
                    {[
                      t("modelOps.local.hfDetails.fileType", { type: file.file_type || "unknown" }),
                      t("modelOps.local.hfDetails.fileSize", { size: formatBytes(file.size, emptyLabel) }),
                    ].join(" · ")}
                  </span>
                  {file.blob_id ? <span className="status-text">{t("modelOps.local.hfDetails.blobId", { blobId: file.blob_id })}</span> : null}
                  {file.lfs ? (
                    <pre className="modelops-json-block">{jsonBlock(file.lfs)}</pre>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="status-text">{emptyLabel}</p>
          )}
        </section>

        {metadataSections.length ? (
          <section className="card-stack">
            <h3 className="section-title">{t("modelOps.local.hfDetails.metadata")}</h3>
            {metadataSections.map((section) => (
              <details key={section.key} className="panel panel-nested card-stack" open>
                <summary className="field-label">{section.label}</summary>
                <pre className="modelops-json-block">{jsonBlock(section.value)}</pre>
              </details>
            ))}
          </section>
        ) : null}
      </div>
    </ModalDialog>
  );
}
