import { useCallback, useEffect, useMemo, useState } from "react";
import { listDownloadJobs, listModelCredentials, listModelOpsModels, type ManagedModel } from "../../../api/models";
import type { Role } from "../../../auth/types";

type SummaryState = {
  models: ManagedModel[];
  credentialCount: number;
  activeDownloadJobs: number;
};

export function useModelOpsSummary(
  token: string,
  role: Role | undefined,
): {
  summary: SummaryState;
  isLoading: boolean;
  error: string;
  refresh: () => Promise<void>;
  cards: Array<{ label: string; value: number }>;
} {
  const [summary, setSummary] = useState<SummaryState>({
    models: [],
    credentialCount: 0,
    activeDownloadJobs: 0,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async (): Promise<void> => {
    if (!token) {
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const [models, credentials, jobs] = await Promise.all([
        listModelOpsModels(token),
        listModelCredentials(token),
        role === "superadmin" ? listDownloadJobs(token) : Promise.resolve([]),
      ]);
      const activeDownloadJobs = jobs.filter((job) => job.status === "queued" || job.status === "running").length;
      setSummary({
        models,
        credentialCount: credentials.length,
        activeDownloadJobs,
      });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load model summary.");
    } finally {
      setIsLoading(false);
    }
  }, [role, token]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const cards = useMemo(() => {
    const models = summary.models;
    const activeCount = models.filter((model) => model.lifecycle_state === "active").length;
    const localCount = models.filter((model) => model.hosting === "local" || model.backend === "local").length;
    const cloudCount = models.filter((model) => model.hosting === "cloud" || model.backend === "external_api").length;
    const validatedCount = models.filter((model) => model.is_validation_current && model.last_validation_status === "success").length;
    const personalCount = models.filter((model) => model.owner_type === "user").length;
    const sharedCount = models.filter((model) => model.visibility_scope && model.visibility_scope !== "private").length;

    if (role === "superadmin") {
      return [
        { label: "Total models", value: models.length },
        { label: "Active models", value: activeCount },
        { label: "Inactive models", value: Math.max(models.length - activeCount, 0) },
        { label: "Local models", value: localCount },
        { label: "Cloud models", value: cloudCount },
        { label: "Validated", value: validatedCount },
        { label: "Personal models", value: personalCount },
        { label: "Shared/platform", value: sharedCount },
        { label: "Active downloads", value: summary.activeDownloadJobs },
      ];
    }

    const accessiblePersonalCount = models.filter(
      (model) => model.owner_type === "user" || model.visibility_scope === "private",
    ).length;
    return [
      { label: "Accessible models", value: models.length },
      { label: "Active models", value: activeCount },
      { label: "Inactive models", value: Math.max(models.length - activeCount, 0) },
      { label: "Personal models", value: accessiblePersonalCount },
      { label: "Saved credentials", value: summary.credentialCount },
    ];
  }, [role, summary]);

  return { summary, isLoading, error, refresh, cards };
}
