import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  listPlatformActivationAudit,
  listPlatformCapabilities,
  listPlatformDeployments,
  type PlatformActivationAuditEntry,
  type PlatformCapability,
  type PlatformDeploymentProfile,
} from "../../../api/platform";
import type { LoadState } from "../utils";

type PlatformOverviewState = {
  state: LoadState;
  errorMessage: string;
  capabilities: PlatformCapability[];
  deployments: PlatformDeploymentProfile[];
  activationAudit: PlatformActivationAuditEntry[];
  reload: () => Promise<void>;
};

export function usePlatformOverview(token: string): PlatformOverviewState {
  const { t } = useTranslation("common");
  const [state, setState] = useState<LoadState>("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [capabilities, setCapabilities] = useState<PlatformCapability[]>([]);
  const [deployments, setDeployments] = useState<PlatformDeploymentProfile[]>([]);
  const [activationAudit, setActivationAudit] = useState<PlatformActivationAuditEntry[]>([]);

  const reload = useCallback(async (): Promise<void> => {
    if (!token) {
      setState("error");
      setErrorMessage(t("platformControl.feedback.authRequired"));
      return;
    }

    setState("loading");
    setErrorMessage("");

    try {
      const [capabilitiesPayload, deploymentsPayload, auditPayload] = await Promise.all([
        listPlatformCapabilities(token),
        listPlatformDeployments(token),
        listPlatformActivationAudit(token),
      ]);
      setCapabilities(capabilitiesPayload);
      setDeployments(deploymentsPayload);
      setActivationAudit(auditPayload);
      setState("success");
    } catch (error) {
      setState("error");
      setErrorMessage(error instanceof Error ? error.message : t("platformControl.feedback.loadFailed"));
    }
  }, [t, token]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return {
    state,
    errorMessage,
    capabilities,
    deployments,
    activationAudit,
    reload,
  };
}
