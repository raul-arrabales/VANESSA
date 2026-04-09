import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { getManagedModel } from "../../../../api/modelops/models";
import { listManagedModelTests, runManagedModelTest, validateManagedModel } from "../../../../api/modelops/testing";
import type { ManagedModel, ModelTestResult, ModelTestRun } from "../../../../api/modelops/types";
import { useActionFeedback } from "../../../../feedback/ActionFeedbackProvider";
import type { ManagedModelTestState, ModelTestInput } from "../types";

export function useManagedModelTest(
  modelId: string | undefined,
  token: string,
): ManagedModelTestState {
  const [model, setModel] = useState<ManagedModel | null>(null);
  const [tests, setTests] = useState<ModelTestRun[]>([]);
  const [latestResult, setLatestResult] = useState<ModelTestResult | null>(null);
  const [pendingTestRunId, setPendingTestRunId] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isRunningTest, setIsRunningTest] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const { t } = useTranslation("common");
  const { showErrorFeedback, showSuccessFeedback } = useActionFeedback();

  const refresh = useCallback(async (): Promise<void> => {
    if (!token || !modelId) {
      return;
    }

    setIsLoading(true);
    try {
      const [modelPayload, testsPayload] = await Promise.all([
        getManagedModel(modelId, token),
        listManagedModelTests(modelId, token),
      ]);
      setModel(modelPayload);
      setTests(testsPayload.tests);
      if (!pendingTestRunId) {
        const latestSuccessful = testsPayload.tests.find((item) => item.result === "success");
        setPendingTestRunId(latestSuccessful?.id ?? "");
      }
    } catch (requestError) {
      showErrorFeedback(requestError, t("modelOps.testing.loadFailed"), {
        titleKey: "modelOps.testing.title",
      });
    } finally {
      setIsLoading(false);
    }
  }, [modelId, pendingTestRunId, showErrorFeedback, t, token]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const latestSuccessfulTestRunId = useMemo(() => {
    if (pendingTestRunId) {
      return pendingTestRunId;
    }
    return tests.find((item) => item.result === "success")?.id ?? "";
  }, [pendingTestRunId, tests]);

  const runTest = useCallback(async (
    inputs: ModelTestInput,
    options?: { providerInstanceId?: string },
  ): Promise<void> => {
    if (!token || !modelId) {
      return;
    }

    setIsRunningTest(true);
    try {
      const payload = await runManagedModelTest(
        modelId,
        {
          inputs,
          provider_instance_id: options?.providerInstanceId,
        },
        token,
      );
      setModel(payload.model);
      setLatestResult(payload.result);
      setPendingTestRunId(payload.test_run.result === "success" ? payload.test_run.id : "");
      if (payload.test_run.result === "success") {
        showSuccessFeedback(t("modelOps.testing.runSucceeded"), {
          titleKey: "modelOps.testing.title",
        });
      } else {
        showErrorFeedback(undefined, t("modelOps.testing.runFailed"), {
          titleKey: "modelOps.testing.title",
        });
      }
      await refresh();
    } catch (requestError) {
      setPendingTestRunId("");
      setLatestResult(null);
      await refresh();
      showErrorFeedback(requestError, t("modelOps.testing.runFailedRequest"), {
        titleKey: "modelOps.testing.title",
      });
    } finally {
      setIsRunningTest(false);
    }
  }, [modelId, refresh, showErrorFeedback, showSuccessFeedback, t, token]);

  const markValidated = useCallback(async (): Promise<void> => {
    if (!token || !modelId || !latestSuccessfulTestRunId) {
      return;
    }

    setIsValidating(true);
    try {
      const nextModel = await validateManagedModel(modelId, token, { testRunId: latestSuccessfulTestRunId });
      setModel(nextModel);
      showSuccessFeedback(t("modelOps.testing.validationConfirmed"), {
        titleKey: "modelOps.testing.title",
      });
      await refresh();
    } catch (requestError) {
      showErrorFeedback(requestError, t("modelOps.testing.validationFailed"), {
        titleKey: "modelOps.testing.title",
      });
    } finally {
      setIsValidating(false);
    }
  }, [latestSuccessfulTestRunId, modelId, refresh, showErrorFeedback, showSuccessFeedback, t, token]);

  return {
    model,
    tests,
    latestResult,
    latestSuccessfulTestRunId,
    isLoading,
    isRunningTest,
    isValidating,
    refresh,
    runTest,
    markValidated,
  };
}
