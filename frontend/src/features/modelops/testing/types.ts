import type { JSX } from "react";
import type { ManagedModel, ModelTestResult, ModelTestRun } from "../../../api/modelops/types";

export type ModelTestInput = Record<string, unknown>;

export type LlmModelTestInput = {
  prompt: string;
};

export type EmbeddingModelTestInput = {
  text: string;
};

export type ModelTestExecutionResult = ModelTestResult;

export type ModelTestPanelRendererProps<TInputs extends ModelTestInput = ModelTestInput> = {
  isPending: boolean;
  defaultInputs: TInputs;
  onRun: (inputs: TInputs) => Promise<void>;
};

export type ModelTestRegistryEntry<TInputs extends ModelTestInput = ModelTestInput> = {
  defaultInputs: TInputs;
  buildRequest: (inputs: TInputs) => ModelTestInput;
  summarizeResult: (
    result: ModelTestExecutionResult | null,
    latestTest: ModelTestRun | null,
  ) => string;
  formatDebugPayload: (latestTest: ModelTestRun | null) => {
    requestPayload: unknown;
    responsePayload: unknown;
  };
  renderPanel: (props: ModelTestPanelRendererProps<TInputs>) => JSX.Element;
};

export type ManagedModelTestState = {
  model: ManagedModel | null;
  tests: ModelTestRun[];
  latestResult: ModelTestExecutionResult | null;
  latestSuccessfulTestRunId: string;
  isLoading: boolean;
  isRunningTest: boolean;
  isValidating: boolean;
  error: string;
  feedback: string;
  refresh: () => Promise<void>;
  runTest: (inputs: ModelTestInput) => Promise<void>;
  markValidated: () => Promise<void>;
};
