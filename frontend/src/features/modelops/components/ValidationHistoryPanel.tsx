import { useTranslation } from "react-i18next";

type ValidationHistoryPanelProps = {
  validations: Array<Record<string, unknown>>;
};

export default function ValidationHistoryPanel({ validations }: ValidationHistoryPanelProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <article className="panel card-stack">
      <h2 className="section-title">{t("modelOps.detail.validationsTitle")}</h2>
      {validations.length === 0 ? (
        <p className="status-text">{t("modelOps.detail.noValidations")}</p>
      ) : (
        <ul className="card-stack" aria-label="Model validations">
          {validations.map((validation, index) => (
            <li key={`${String(validation.id ?? index)}`} className="status-row">
              <span>
                {`${String(validation.result ?? "unknown")} · ${String(validation.summary ?? "No summary")}`}
              </span>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
