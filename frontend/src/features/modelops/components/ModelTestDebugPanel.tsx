import { useTranslation } from "react-i18next";
import type { ModelTestRun } from "../../../api/models";

type ModelTestDebugPanelProps = {
  latestTest: ModelTestRun | null;
};

export default function ModelTestDebugPanel({ latestTest }: ModelTestDebugPanelProps): JSX.Element | null {
  const { t } = useTranslation("common");

  if (!latestTest) {
    return null;
  }

  return (
    <article className="panel card-stack">
      <details>
        <summary>{t("modelOps.testing.debugTitle")}</summary>
        <div className="card-stack">
          <pre className="status-text">{JSON.stringify(latestTest.input_payload ?? {}, null, 2)}</pre>
          <pre className="status-text">{JSON.stringify(latestTest.output_payload ?? latestTest.error_details ?? {}, null, 2)}</pre>
        </div>
      </details>
    </article>
  );
}
