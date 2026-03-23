import { useTranslation } from "react-i18next";
import type { PlatformActivationAuditEntry } from "../../../api/platform";

type PlatformDeploymentAuditTableProps = {
  entries: PlatformActivationAuditEntry[];
  title?: string;
  description?: string;
};

export default function PlatformDeploymentAuditTable({
  entries,
  title,
  description,
}: PlatformDeploymentAuditTableProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h3 className="section-title">{title ?? t("platformControl.sections.audit")}</h3>
        <p className="status-text">{description ?? t("platformControl.audit.description")}</p>
      </div>
      {entries.length === 0 ? (
        <p className="status-text">{t("platformControl.audit.empty")}</p>
      ) : (
        <div className="health-table-wrap">
          <table className="health-table" aria-label={t("platformControl.audit.tableAria")}>
            <thead>
              <tr>
                <th>{t("platformControl.audit.columns.activatedAt")}</th>
                <th>{t("platformControl.audit.columns.deployment")}</th>
                <th>{t("platformControl.audit.columns.previousDeployment")}</th>
                <th>{t("platformControl.audit.columns.actor")}</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id}>
                  <td>{entry.activated_at}</td>
                  <td>{entry.deployment_profile.display_name}</td>
                  <td>{entry.previous_deployment_profile?.display_name ?? t("platformControl.summary.none")}</td>
                  <td>{entry.activated_by_user_id ?? t("platformControl.summary.none")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </article>
  );
}
