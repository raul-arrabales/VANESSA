import type { HfModelDetails, HfModelFileDetails } from "../../../api/modelops/types";
import {
  formatBytes,
  formatOptionalValue,
  jsonBlock,
  type HfModelDetailMetadataSection,
} from "./hfModelDetailPresentation";

type HfModelDetailSectionProps = {
  emptyLabel: string;
  t: (key: string, options?: Record<string, unknown>) => string;
};

type HfModelIdentityGridProps = HfModelDetailSectionProps & {
  model: HfModelDetails;
};

export function HfModelIdentityGrid({
  model,
  emptyLabel,
  t,
}: HfModelIdentityGridProps): JSX.Element {
  const entries = [
    { label: t("modelOps.local.hfDetails.name"), value: formatOptionalValue(model.name, emptyLabel) },
    { label: t("modelOps.local.hfDetails.author"), value: formatOptionalValue(model.author, emptyLabel) },
    { label: t("modelOps.local.hfDetails.pipeline"), value: formatOptionalValue(model.pipeline_tag, emptyLabel) },
    { label: t("modelOps.local.hfDetails.library"), value: formatOptionalValue(model.library_name, emptyLabel) },
    { label: t("modelOps.local.hfDetails.downloads"), value: formatOptionalValue(model.downloads, emptyLabel) },
    { label: t("modelOps.local.hfDetails.likes"), value: formatOptionalValue(model.likes, emptyLabel) },
    { label: t("modelOps.local.hfDetails.sha"), value: formatOptionalValue(model.sha, emptyLabel) },
    { label: t("modelOps.local.hfDetails.gated"), value: formatOptionalValue(model.gated, emptyLabel) },
    { label: t("modelOps.local.hfDetails.private"), value: formatOptionalValue(model.private, emptyLabel) },
    { label: t("modelOps.local.hfDetails.disabled"), value: formatOptionalValue(model.disabled, emptyLabel) },
    { label: t("modelOps.local.hfDetails.usedStorage"), value: formatBytes(model.used_storage, emptyLabel) },
    { label: t("modelOps.local.hfDetails.lastModified"), value: formatOptionalValue(model.last_modified, emptyLabel) },
  ];

  return (
    <dl className="modelops-detail-grid">
      {entries.map((entry) => (
        <div key={entry.label}>
          <dt>{entry.label}</dt>
          <dd>{entry.value}</dd>
        </div>
      ))}
    </dl>
  );
}

type HfModelTagsSectionProps = HfModelDetailSectionProps & {
  tags: string[];
};

export function HfModelTagsSection({
  tags,
  emptyLabel,
  t,
}: HfModelTagsSectionProps): JSX.Element {
  return (
    <section className="card-stack">
      <h3 className="section-title">{t("modelOps.local.hfDetails.tags")}</h3>
      {tags.length ? (
        <div className="button-row">
          {tags.map((tag) => (
            <span key={tag} className="status-chip status-chip-neutral">{tag}</span>
          ))}
        </div>
      ) : (
        <p className="status-text">{emptyLabel}</p>
      )}
    </section>
  );
}

type HfModelFileFormatsSectionProps = HfModelDetailSectionProps & {
  formatSummary: Array<{ type: string; count: number }>;
};

export function HfModelFileFormatsSection({
  formatSummary,
  emptyLabel,
  t,
}: HfModelFileFormatsSectionProps): JSX.Element {
  return (
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
  );
}

type HfModelFileListSectionProps = HfModelDetailSectionProps & {
  files: HfModelFileDetails[];
};

export function HfModelFileListSection({
  files,
  emptyLabel,
  t,
}: HfModelFileListSectionProps): JSX.Element {
  return (
    <section className="card-stack">
      <h3 className="section-title">{t("modelOps.local.hfDetails.files")}</h3>
      {files.length ? (
        <ul className="card-stack">
          {files.map((file) => (
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
  );
}

type HfModelMetadataSectionsProps = {
  metadataSections: HfModelDetailMetadataSection[];
  t: (key: string, options?: Record<string, unknown>) => string;
};

export function HfModelMetadataSections({
  metadataSections,
  t,
}: HfModelMetadataSectionsProps): JSX.Element | null {
  if (!metadataSections.length) {
    return null;
  }

  return (
    <section className="card-stack">
      <h3 className="section-title">{t("modelOps.local.hfDetails.metadata")}</h3>
      {metadataSections.map((section) => (
        <details key={section.key} className="panel panel-nested card-stack" open>
          <summary className="field-label">{section.label}</summary>
          <pre className="modelops-json-block">{jsonBlock(section.value)}</pre>
        </details>
      ))}
    </section>
  );
}
