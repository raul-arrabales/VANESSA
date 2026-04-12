import { useTranslation } from "react-i18next";
import type { ModelDownloadJob } from "../../../api/modelops/types";

type LocalDownloadsPanelProps = {
  downloadJobs: ModelDownloadJob[];
  hasActiveJobs: boolean;
};

export default function LocalDownloadsPanel({
  downloadJobs,
  hasActiveJobs,
}: LocalDownloadsPanelProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <article className="panel card-stack">
      <h2 className="section-title">{t("modelOps.local.activeDownloadsTitle")}</h2>
      <p className="status-text">
        {hasActiveJobs ? t("modelOps.local.pollingActive") : t("modelOps.local.noActiveJobs")}
      </p>
      <ul className="card-stack" aria-label={t("modelOps.local.downloadJobsAria")}>
        {downloadJobs.map((job) => (
          <li key={job.job_id} className="status-row">
            <span>{`${job.source_id} · ${job.status}`}</span>
            {job.error_message && <span className="error-text">{job.error_message}</span>}
          </li>
        ))}
      </ul>
    </article>
  );
}
