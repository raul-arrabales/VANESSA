import { useTranslation } from "react-i18next";
import type { ModelValidationRecord } from "../../../api/modelops/types";

type ValidationHistoryPanelProps = {
  validations: ModelValidationRecord[];
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
            <li key={validation.id || `${index}`} className="status-row">
              <span>
                {`${validation.result || "unknown"} · ${validation.summary || "No summary"}`}
              </span>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
