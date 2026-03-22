import { requestJson } from "./request";
import type { ManagedModel, ModelTestResult, ModelTestRun } from "./types";

export async function listManagedModelTests(
  modelId: string,
  token: string,
  limit = 10,
): Promise<{
  model_id: string;
  tests: ModelTestRun[];
}> {
  return requestJson<{
    model_id: string;
    tests: ModelTestRun[];
  }>(`/v1/modelops/models/${encodeURIComponent(modelId)}/tests?limit=${encodeURIComponent(String(limit))}`, { token });
}

export async function runManagedModelTest(
  modelId: string,
  payload: { inputs: Record<string, unknown> },
  token: string,
): Promise<{
  model: ManagedModel;
  test_run: ModelTestRun;
  result: ModelTestResult;
}> {
  return requestJson<{
    model: ManagedModel;
    test_run: ModelTestRun;
    result: ModelTestResult;
  }>(`/v1/modelops/models/${encodeURIComponent(modelId)}/test`, {
    method: "POST",
    token,
    body: payload,
  });
}

export async function validateManagedModel(
  modelId: string,
  token: string,
  options: { testRunId: string },
): Promise<ManagedModel> {
  const result = await requestJson<{ model: ManagedModel }>(`/v1/modelops/models/${encodeURIComponent(modelId)}/validate`, {
    method: "POST",
    token,
    body: { test_run_id: options.testRunId },
  });
  return result.model;
}
