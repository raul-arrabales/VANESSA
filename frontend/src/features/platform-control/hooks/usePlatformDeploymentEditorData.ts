import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { listModelOpsModels, type ManagedModel } from "../../../api/modelops";
import {
  listPlatformActivationAudit,
  listPlatformCapabilities,
  listPlatformDeployments,
  listPlatformProviders,
  type PlatformActivationAuditEntry,
  type PlatformCapability,
  type PlatformDeploymentProfile,
  type PlatformProvider,
} from "../../../api/platform";
import type { LoadState } from "../utils";

type PlatformDeploymentEditorDataState = {
  state: LoadState;
  errorMessage: string;
  capabilities: PlatformCapability[];
  providers: PlatformProvider[];
  deployments: PlatformDeploymentProfile[];
  activationAudit: PlatformActivationAuditEntry[];
  eligibleModelsByCapability: Record<string, ManagedModel[]>;
  reload: () => Promise<void>;
};

export function usePlatformDeploymentEditorData(token: string): PlatformDeploymentEditorDataState {
  const { t } = useTranslation("common");
  const [state, setState] = useState<LoadState>("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [capabilities, setCapabilities] = useState<PlatformCapability[]>([]);
  const [providers, setProviders] = useState<PlatformProvider[]>([]);
  const [deployments, setDeployments] = useState<PlatformDeploymentProfile[]>([]);
  const [activationAudit, setActivationAudit] = useState<PlatformActivationAuditEntry[]>([]);
  const [eligibleModelsByCapability, setEligibleModelsByCapability] = useState<Record<string, ManagedModel[]>>({});

  const reload = useCallback(async (): Promise<void> => {
    if (!token) {
      setState("error");
      setErrorMessage(t("platformControl.feedback.authRequired"));
      return;
    }

    setState("loading");
    setErrorMessage("");

    try {
      const [
        capabilitiesPayload,
        providersPayload,
        deploymentsPayload,
        activationAuditPayload,
        llmModelsPayload,
        embeddingsModelsPayload,
      ] = await Promise.all([
        listPlatformCapabilities(token),
        listPlatformProviders(token),
        listPlatformDeployments(token),
        listPlatformActivationAudit(token),
        listModelOpsModels(token, { eligible: true, capability: "llm_inference" }),
        listModelOpsModels(token, { eligible: true, capability: "embeddings" }),
      ]);

      setCapabilities(capabilitiesPayload);
      setProviders(providersPayload);
      setDeployments(deploymentsPayload);
      setActivationAudit(activationAuditPayload);
      setEligibleModelsByCapability({
        llm_inference: llmModelsPayload,
        embeddings: embeddingsModelsPayload,
      });
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
    providers,
    deployments,
    activationAudit,
    eligibleModelsByCapability,
    reload,
  };
}
