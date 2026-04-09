import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { listModelOpsModels } from "../../../api/modelops/models";
import { listModelCredentials } from "../../../api/modelops/credentials";
import { listDownloadJobs } from "../../../api/modelops/local";
import type { ManagedModel } from "../../../api/modelops/types";
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
  const { t } = useTranslation("common");
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
      setError(requestError instanceof Error ? requestError.message : t("modelOps.home.loadFailed"));
    } finally {
      setIsLoading(false);
    }
  }, [role, t, token]);

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
        { label: t("modelOps.home.summaryCards.totalModels"), value: models.length },
        { label: t("modelOps.home.summaryCards.activeModels"), value: activeCount },
        { label: t("modelOps.home.summaryCards.inactiveModels"), value: Math.max(models.length - activeCount, 0) },
        { label: t("modelOps.home.summaryCards.localModels"), value: localCount },
        { label: t("modelOps.home.summaryCards.cloudModels"), value: cloudCount },
        { label: t("modelOps.home.summaryCards.validated"), value: validatedCount },
        { label: t("modelOps.home.summaryCards.personalModels"), value: personalCount },
        { label: t("modelOps.home.summaryCards.sharedPlatform"), value: sharedCount },
        { label: t("modelOps.home.summaryCards.activeDownloads"), value: summary.activeDownloadJobs },
      ];
    }

    const accessiblePersonalCount = models.filter(
      (model) => model.owner_type === "user" || model.visibility_scope === "private",
    ).length;
    return [
      { label: t("modelOps.home.summaryCards.accessibleModels"), value: models.length },
      { label: t("modelOps.home.summaryCards.activeModels"), value: activeCount },
      { label: t("modelOps.home.summaryCards.inactiveModels"), value: Math.max(models.length - activeCount, 0) },
      { label: t("modelOps.home.summaryCards.personalModels"), value: accessiblePersonalCount },
      { label: t("modelOps.home.summaryCards.savedCredentials"), value: summary.credentialCount },
    ];
  }, [role, summary, t]);

  return { summary, isLoading, error, refresh, cards };
}
