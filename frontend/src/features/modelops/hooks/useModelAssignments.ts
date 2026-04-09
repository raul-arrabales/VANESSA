import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { listModelOpsModels } from "../../../api/modelops/models";
import { listModelAssignments, updateModelAssignment } from "../../../api/modelops/access";
import type { ManagedModel, ModelScopeAssignment } from "../../../api/modelops/types";

export function useModelAssignments(token: string): {
  models: ManagedModel[];
  assignments: ModelScopeAssignment[];
  assignmentByScope: Map<string, string[]>;
  isLoading: boolean;
  error: string;
  feedback: string;
  refresh: () => Promise<void>;
  toggleAssignment: (scope: string, modelId: string) => Promise<void>;
} {
  const { t } = useTranslation("common");
  const [models, setModels] = useState<ManagedModel[]>([]);
  const [assignments, setAssignments] = useState<ModelScopeAssignment[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");

  const refresh = useCallback(async (): Promise<void> => {
    if (!token) {
      return;
    }

    setIsLoading(true);
    setError("");
    try {
      const [modelRows, assignmentRows] = await Promise.all([
        listModelOpsModels(token),
        listModelAssignments(token),
      ]);
      setModels(modelRows);
      setAssignments(assignmentRows);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : t("modelOps.access.loadFailed"));
    } finally {
      setIsLoading(false);
    }
  }, [t, token]);

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

    setError("");
    setFeedback("");
    try {
      const saved = await updateModelAssignment(scope, next, token);
      setAssignments((currentAssignments) => {
        const others = currentAssignments.filter((assignment) => assignment.scope !== scope);
        return [...others, saved];
      });
      setFeedback(t("modelOps.access.saved", { scope }));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : t("modelOps.access.saveFailed"));
    }
  }, [assignmentByScope, t, token]);

  return {
    models,
    assignments,
    assignmentByScope,
    isLoading,
    error,
    feedback,
    refresh,
    toggleAssignment,
  };
}
