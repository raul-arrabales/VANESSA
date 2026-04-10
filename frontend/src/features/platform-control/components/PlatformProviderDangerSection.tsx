import { useTranslation } from "react-i18next";

type PlatformProviderDangerSectionProps = {
  confirmDelete: boolean;
  onDelete: () => void;
  onToggleConfirmDelete: (nextValue: boolean) => void;
};

export default function PlatformProviderDangerSection({
  confirmDelete,
  onDelete,
  onToggleConfirmDelete,
}: PlatformProviderDangerSectionProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <article className="panel card-stack">
      <div className="status-row">
        <h3 className="section-title">{t("platformControl.sections.danger")}</h3>
        <p className="status-text">{t("platformControl.providers.deleteDescription")}</p>
      </div>
      <div className="inline-meta-list">
        {confirmDelete ? (
          <>
            <button type="button" className="btn btn-secondary" onClick={() => onToggleConfirmDelete(false)}>
              {t("platformControl.actions.cancel")}
            </button>
            <button type="button" className="btn btn-primary" onClick={onDelete}>
              {t("platformControl.actions.confirmDelete")}
            </button>
          </>
        ) : (
          <button type="button" className="btn btn-secondary" onClick={() => onToggleConfirmDelete(true)}>
            {t("platformControl.actions.delete")}
          </button>
        )}
      </div>
    </article>
  );
}
