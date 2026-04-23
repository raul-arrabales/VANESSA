import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { testCatalogTool, type CatalogTool, type CatalogToolTestResult } from "../../../api/catalog";
import { useActionFeedback } from "../../../feedback/ActionFeedbackProvider";
import { buildSampleToolInput } from "../catalogToolTestSamples";

export type ToolTestFormState = {
  toolId: string;
  inputText: string;
};

export const DEFAULT_TOOL_TEST_FORM: ToolTestFormState = {
  toolId: "",
  inputText: "{}",
};

function stringifyJson(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2);
}

function parseJsonObject(text: string, errorMessage: string): Record<string, unknown> {
  const normalized = text.trim();
  if (!normalized) {
    return {};
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(normalized);
  } catch {
    throw new Error(errorMessage);
  }

  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(errorMessage);
  }

  return parsed as Record<string, unknown>;
}

export function buildToolTestForm(tool: CatalogTool): ToolTestFormState {
  return {
    toolId: tool.id,
    inputText: stringifyJson(buildSampleToolInput(tool)),
  };
}

export function useCatalogToolTesting(token: string) {
  const { t } = useTranslation("common");
  const { showErrorFeedback } = useActionFeedback();
  const [toolTestForm, setToolTestForm] = useState<ToolTestFormState>(DEFAULT_TOOL_TEST_FORM);
  const [toolTestResult, setToolTestResult] = useState<CatalogToolTestResult | null>(null);
  const [toolTestError, setToolTestError] = useState("");
  const [testingToolId, setTestingToolId] = useState("");

  const handleToolTest = useCallback(async (): Promise<CatalogToolTestResult | null> => {
    if (!token || !toolTestForm.toolId) {
      return null;
    }
    setTestingToolId(toolTestForm.toolId);
    setToolTestError("");
    try {
      const input = parseJsonObject(
        toolTestForm.inputText,
        t("catalogControl.feedback.invalidJson", { field: t("catalogControl.forms.toolTest.input") }),
      );
      const result = await testCatalogTool(toolTestForm.toolId, input, token);
      setToolTestResult(result);
      return result;
    } catch (error) {
      setToolTestResult(null);
      const message = error instanceof Error ? error.message : t("catalogControl.feedback.toolTestFailed");
      setToolTestError(message);
      showErrorFeedback(error, t("catalogControl.feedback.toolTestFailed"));
      return null;
    } finally {
      setTestingToolId("");
    }
  }, [showErrorFeedback, t, token, toolTestForm.inputText, toolTestForm.toolId]);

  const openToolTester = useCallback((tool: CatalogTool) => {
    setToolTestForm(buildToolTestForm(tool));
    setToolTestResult(null);
    setToolTestError("");
  }, []);

  const resetToolTester = useCallback(() => {
    setToolTestForm(DEFAULT_TOOL_TEST_FORM);
    setToolTestResult(null);
    setToolTestError("");
  }, []);

  return {
    toolTestForm,
    setToolTestForm,
    toolTestResult,
    toolTestError,
    testingToolId,
    handleToolTest,
    openToolTester,
    resetToolTester,
  };
}
