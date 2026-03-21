import { useCallback, useEffect, useMemo, useState } from "react";
import {
  getManagedModel,
  listManagedModelTests,
  runManagedModelTest,
  validateManagedModel,
  type ManagedModel,
  type ModelTestResult,
  type ModelTestRun,
} from "../../../api/models";

export function useManagedModelTest(
  modelId: string | undefined,
  token: string,
): {
  model: ManagedModel | null;
  tests: ModelTestRun[];
  latestResult: ModelTestResult | null;
  latestSuccessfulTestRunId: string;
  isLoading: boolean;
  isRunningTest: boolean;
  isValidating: boolean;
  error: string;
  feedback: string;
  refresh: () => Promise<void>;
  runTest: (inputs: Record<string, unknown>) => Promise<void>;
  markValidated: () => Promise<void>;
} {
  const [model, setModel] = useState<ManagedModel | null>(null);
  const [tests, setTests] = useState<ModelTestRun[]>([]);
  const [latestResult, setLatestResult] = useState<ModelTestResult | null>(null);
  const [pendingTestRunId, setPendingTestRunId] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isRunningTest, setIsRunningTest] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");

  const refresh = useCallback(async (): Promise<void> => {
    if (!token || !modelId) {
      return;
    }

    setIsLoading(true);
    setError("");
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
      setError(requestError instanceof Error ? requestError.message : "Unable to load model test page.");
    } finally {
      setIsLoading(false);
    }
  }, [modelId, pendingTestRunId, token]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const latestSuccessfulTestRunId = useMemo(() => {
    if (pendingTestRunId) {
      return pendingTestRunId;
    }
    return tests.find((item) => item.result === "success")?.id ?? "";
  }, [pendingTestRunId, tests]);

  const runTest = useCallback(async (inputs: Record<string, unknown>): Promise<void> => {
    if (!token || !modelId) {
      return;
    }

    setIsRunningTest(true);
    setError("");
    setFeedback("");
    try {
      const payload = await runManagedModelTest(modelId, { inputs }, token);
      setModel(payload.model);
      setLatestResult(payload.result);
      setPendingTestRunId(payload.test_run.result === "success" ? payload.test_run.id : "");
      setFeedback(payload.test_run.result === "success" ? "Model test succeeded." : "Model test failed.");
      await refresh();
    } catch (requestError) {
      setPendingTestRunId("");
      setLatestResult(null);
      await refresh();
      setError(requestError instanceof Error ? requestError.message : "Unable to run model test.");
    } finally {
      setIsRunningTest(false);
    }
  }, [modelId, refresh, token]);

  const markValidated = useCallback(async (): Promise<void> => {
    if (!token || !modelId || !latestSuccessfulTestRunId) {
      return;
    }

    setIsValidating(true);
    setError("");
    setFeedback("");
    try {
      const nextModel = await validateManagedModel(modelId, token, { testRunId: latestSuccessfulTestRunId });
      setModel(nextModel);
      setFeedback("Model marked as validated.");
      await refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to validate model.");
    } finally {
      setIsValidating(false);
    }
  }, [latestSuccessfulTestRunId, modelId, refresh, token]);

  return {
    model,
    tests,
    latestResult,
    latestSuccessfulTestRunId,
    isLoading,
    isRunningTest,
    isValidating,
    error,
    feedback,
    refresh,
    runTest,
    markValidated,
  };
}
