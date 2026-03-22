import { useTranslation } from "react-i18next";
import type { ManagedModel, ModelTestRun } from "../../../../api/models";

type ModelTestHeaderProps = {
  model: ManagedModel;
  latestTest: ModelTestRun | null;
};

export default function ModelTestHeader({ model, latestTest }: ModelTestHeaderProps): JSX.Element {
  const { t } = useTranslation("common");

  return (
    <article className="panel card-stack">
      <h2 className="section-title">{model.name}</h2>
      <p className="status-text">{model.id}</p>
      <p className="status-text">
        {`${model.task_key ?? "unknown"} · ${model.hosting ?? model.backend} · ${model.lifecycle_state ?? "unknown"}`}
      </p>
      <p className="status-text">
        {`${t("modelOps.testing.validationStatus")}: ${model.last_validation_status ?? "pending"} · ${t("modelOps.testing.currentValidation")}: ${model.is_validation_current ? "yes" : "no"}`}
      </p>
      <p className="status-text">
        {latestTest
          ? t("modelOps.testing.lastTestSummary", {
              result: latestTest.result,
              timestamp: latestTest.created_at ?? "--",
            })
          : t("modelOps.testing.noTests")}
      </p>
    </article>
  );
}
