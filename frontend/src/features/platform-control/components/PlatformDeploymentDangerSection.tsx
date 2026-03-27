import { useTranslation } from "react-i18next";

type PlatformDeploymentDangerSectionProps = {
  confirmDelete: boolean;
  deploymentIsActive: boolean;
  onDelete: () => void;
  onToggleConfirmDelete: (nextValue: boolean) => void;
};

export default function PlatformDeploymentDangerSection({
  confirmDelete,
  deploymentIsActive,
  onDelete,
  onToggleConfirmDelete,
}: PlatformDeploymentDangerSectionProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h3 className="section-title">{t("platformControl.sections.danger")}</h3>
        <p className="status-text">{t("platformControl.deployments.deleteDescription")}</p>
      </div>
      <div className="platform-inline-meta">
        {confirmDelete ? (
          <>
            <button type="button" className="btn btn-secondary" onClick={() => onToggleConfirmDelete(false)}>
              {t("platformControl.actions.cancel")}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onDelete}
              disabled={deploymentIsActive}
            >
              {t("platformControl.actions.confirmDelete")}
            </button>
          </>
        ) : (
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => onToggleConfirmDelete(true)}
            disabled={deploymentIsActive}
          >
            {t("platformControl.actions.delete")}
          </button>
        )}
      </div>
    </article>
  );
}
