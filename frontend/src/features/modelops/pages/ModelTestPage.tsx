import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../../auth/AuthProvider";
import { listManagedModelTestRuntimes } from "../../../api/modelops/testing";
import type { ManagedModelTestRuntime } from "../../../api/modelops/types";
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
  const [runtimes, setRuntimes] = useState<ManagedModelTestRuntime[]>([]);
  const [selectedRuntimeId, setSelectedRuntimeId] = useState("");
  const [isLoadingRuntimes, setIsLoadingRuntimes] = useState(false);
  const [runtimeError, setRuntimeError] = useState("");

  const latestTest = useMemo(() => testState.tests[0] ?? null, [testState.tests]);
  const isSuperadmin = user?.role === "superadmin";
  const needsRuntimeSelection = isSuperadmin && testState.model?.backend === "local" && testState.model?.task_key === "llm";

  useEffect(() => {
    if (!token || !modelId || !needsRuntimeSelection) {
      setRuntimes([]);
      setSelectedRuntimeId("");
      setIsLoadingRuntimes(false);
      setRuntimeError("");
      return;
    }

    let isActive = true;
    setIsLoadingRuntimes(true);
    setRuntimeError("");
    void listManagedModelTestRuntimes(modelId, token)
      .then((payload) => {
        if (!isActive) {
          return;
        }
        setRuntimes(payload.runtimes);
        setSelectedRuntimeId(String(payload.default_provider_instance_id ?? ""));
      })
      .catch((requestError) => {
        if (!isActive) {
          return;
        }
        setRuntimes([]);
        setSelectedRuntimeId("");
        setRuntimeError(requestError instanceof Error ? requestError.message : t("modelOps.testing.runtimeLoadFailed"));
      })
      .finally(() => {
        if (isActive) {
          setIsLoadingRuntimes(false);
        }
      });

    return () => {
      isActive = false;
    };
  }, [modelId, needsRuntimeSelection, t, token]);

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
  const selectedRuntime = runtimes.find((runtime) => runtime.provider_instance_id === selectedRuntimeId) ?? null;
  const hasCompatibleRuntime = runtimes.some((runtime) => runtime.matches_model);
  const runtimeSelectionRequired = needsRuntimeSelection;
  const runDisabled = Boolean(
    runtimeSelectionRequired
      && (isLoadingRuntimes || !selectedRuntime || !selectedRuntime.matches_model),
  );
  const runtimeStatusMessage = runtimeError
    || (runtimeSelectionRequired && !isLoadingRuntimes && !hasCompatibleRuntime
      ? t("modelOps.testing.noCompatibleRuntime")
      : selectedRuntime && !selectedRuntime.matches_model
      ? t("modelOps.testing.runtimeMismatch")
      : "");

  return (
    <section className="card-stack">
      <div className="button-row">
        <Link className="btn btn-secondary" to={`/control/models/${encodeURIComponent(testState.model.id)}`}>
          {t("modelOps.actions.openDetail")}
        </Link>
      </div>

      <ModelTestHeader model={testState.model} latestTest={latestTest} />

      {runtimeSelectionRequired && (
        <article className="panel card-stack">
          <h2 className="section-title">{t("modelOps.testing.runtimeTitle")}</h2>
          <p className="status-text">{t("modelOps.testing.runtimeDescription")}</p>
          <label className="field-label" htmlFor="model-test-runtime">
            {t("modelOps.testing.runtimeLabel")}
          </label>
          <select
            id="model-test-runtime"
            className="field-input"
            value={selectedRuntimeId}
            disabled={isLoadingRuntimes || runtimes.length === 0}
            onChange={(event) => setSelectedRuntimeId(event.currentTarget.value)}
          >
            <option value="">{t("modelOps.testing.runtimePlaceholder")}</option>
            {runtimes.map((runtime) => (
              <option key={runtime.provider_instance_id} value={runtime.provider_instance_id}>
                {runtime.display_name}
                {runtime.is_active ? ` (${t("modelOps.testing.runtimeActive")})` : ""}
                {runtime.matches_model ? ` - ${t("modelOps.testing.runtimeCompatible")}` : ""}
              </option>
            ))}
          </select>
          {isLoadingRuntimes && <p className="status-text">{t("modelOps.states.loading")}</p>}
          {selectedRuntime && (
            <p className="status-text">
              {selectedRuntime.message}
              {selectedRuntime.matched_model_id ? ` (${selectedRuntime.matched_model_id})` : ""}
            </p>
          )}
          {runtimeStatusMessage && <p className={runtimeError ? "error-text" : "status-text"}>{runtimeStatusMessage}</p>}
        </article>
      )}

      {registryEntry ? (
        registryEntry.renderPanel({
          isPending: testState.isRunningTest,
          defaultInputs: registryEntry.defaultInputs,
          runDisabled,
          onRun: async (inputs) => {
            await testState.runTest(
              registryEntry.buildRequest(inputs),
              selectedRuntimeId ? { providerInstanceId: selectedRuntimeId } : undefined,
            );
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
