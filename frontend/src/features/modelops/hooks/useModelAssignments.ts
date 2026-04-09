import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { listModelOpsModels } from "../../../api/modelops/models";
import { listModelAssignments, updateModelAssignment } from "../../../api/modelops/access";
import type { ManagedModel, ModelScopeAssignment } from "../../../api/modelops/types";
import { useActionFeedback } from "../../../feedback/ActionFeedbackProvider";

export function useModelAssignments(token: string): {
  models: ManagedModel[];
  assignments: ModelScopeAssignment[];
  assignmentByScope: Map<string, string[]>;
  isLoading: boolean;
  refresh: () => Promise<void>;
  toggleAssignment: (scope: string, modelId: string) => Promise<void>;
} {
  const { t } = useTranslation("common");
  const { showErrorFeedback, showSuccessFeedback } = useActionFeedback();
  const [models, setModels] = useState<ManagedModel[]>([]);
  const [assignments, setAssignments] = useState<ModelScopeAssignment[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const refresh = useCallback(async (): Promise<void> => {
    if (!token) {
      return;
    }

    setIsLoading(true);
    try {
      const [modelRows, assignmentRows] = await Promise.all([
        listModelOpsModels(token),
        listModelAssignments(token),
      ]);
      setModels(modelRows);
      setAssignments(assignmentRows);
    } catch (requestError) {
      showErrorFeedback(requestError, t("modelOps.access.loadFailed"), {
        titleKey: "modelOps.access.title",
      });
    } finally {
      setIsLoading(false);
    }
  }, [showErrorFeedback, t, token]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const assignmentByScope = useMemo(() => {
    const map = new Map<string, string[]>();
    assignments.forEach((assignment) => {
      map.set(assignment.scope, assignment.model_ids);
    });
    return map;
  }, [assignments]);

  const toggleAssignment = useCallback(async (scope: string, modelId: string): Promise<void> => {
    if (!token) {
      return;
    }

    const current = assignmentByScope.get(scope) ?? [];
    const next = current.includes(modelId) ? current.filter((id) => id !== modelId) : [...current, modelId];

    try {
      const saved = await updateModelAssignment(scope, next, token);
      setAssignments((currentAssignments) => {
        const others = currentAssignments.filter((assignment) => assignment.scope !== scope);
        return [...others, saved];
      });
      showSuccessFeedback(t("modelOps.access.saved", { scope }), {
        titleKey: "modelOps.access.title",
      });
    } catch (requestError) {
      showErrorFeedback(requestError, t("modelOps.access.saveFailed"), {
        titleKey: "modelOps.access.title",
      });
    }
  }, [assignmentByScope, showErrorFeedback, showSuccessFeedback, t, token]);

  return {
    models,
    assignments,
    assignmentByScope,
    isLoading,
    refresh,
    toggleAssignment,
  };
}
