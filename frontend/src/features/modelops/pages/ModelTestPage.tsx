import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../../auth/AuthProvider";
import ModelTestDebugPanel from "../testing/components/ModelTestDebugPanel";
import ModelTestHeader from "../testing/components/ModelTestHeader";
import ModelTestResultPanel from "../testing/components/ModelTestResultPanel";
import ModelValidationAction from "../testing/components/ModelValidationAction";
import { useManagedModelTest } from "../testing/hooks/useManagedModelTest";
import { modelTestRegistry } from "../testing/registry/modelTestRegistry";

export default function ModelTestPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { modelId } = useParams();
  const { token, user } = useAuth();
  const testState = useManagedModelTest(modelId, token);

  const latestTest = useMemo(() => testState.tests[0] ?? null, [testState.tests]);

  if (testState.isLoading) {
    return <p className="status-text">{t("modelOps.states.loading")}</p>;
  }

  if (!testState.model) {
    return (
      <section className="panel card-stack">
        <h2 className="section-title">{t("modelOps.testing.title")}</h2>
        <p className="status-text">{testState.error || t("modelOps.detail.notFound")}</p>
      </section>
    );
  }

  const registryEntry = testState.model.task_key ? modelTestRegistry[testState.model.task_key] : undefined;
  const canValidate = user?.role === "admin" || user?.role === "superadmin";
  const resultSummary = registryEntry?.summarizeResult(testState.latestResult, latestTest) ?? "";
  const debugPayload = registryEntry?.formatDebugPayload(latestTest) ?? {
    requestPayload: latestTest?.input_payload ?? null,
    responsePayload: latestTest?.output_payload ?? latestTest?.error_details ?? null,
  };

  return (
    <section className="card-stack">
      <div className="button-row">
        <Link className="btn btn-secondary" to={`/control/models/${encodeURIComponent(testState.model.id)}`}>
          {t("modelOps.actions.openDetail")}
        </Link>
      </div>

      <ModelTestHeader model={testState.model} latestTest={latestTest} />

      {registryEntry ? (
        registryEntry.renderPanel({
          isPending: testState.isRunningTest,
          defaultInputs: registryEntry.defaultInputs,
          onRun: async (inputs) => {
            await testState.runTest(registryEntry.buildRequest(inputs));
          },
        })
      ) : (
        <article className="panel card-stack">
          <h2 className="section-title">{t("modelOps.testing.unsupportedTitle")}</h2>
          <p className="status-text">{t("modelOps.testing.unsupportedDescription")}</p>
        </article>
      )}

      <ModelTestResultPanel
        result={testState.latestResult}
        latestTest={latestTest}
        summary={resultSummary}
        error={testState.error}
      />

      <ModelValidationAction
        canValidate={canValidate && Boolean(registryEntry)}
        latestSuccessfulTestRunId={testState.latestSuccessfulTestRunId}
        isPending={testState.isValidating}
        onValidate={testState.markValidated}
      />

      <ModelTestDebugPanel
        requestPayload={debugPayload.requestPayload}
        responsePayload={debugPayload.responsePayload}
      />

      {testState.feedback && <p className="status-text">{testState.feedback}</p>}
    </section>
  );
}
