import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  listPlatformCapabilities,
  listPlatformDeployments,
  listPlatformProviderFamilies,
  listPlatformProviders,
  type PlatformCapability,
  type PlatformDeploymentProfile,
  type PlatformProvider,
  type PlatformProviderFamily,
} from "../../../api/platform";
import type { LoadState } from "../platformControlState";

type PlatformProvidersDataState = {
  state: LoadState;
  errorMessage: string;
  capabilities: PlatformCapability[];
  providers: PlatformProvider[];
  providerFamilies: PlatformProviderFamily[];
  deployments: PlatformDeploymentProfile[];
  reload: () => Promise<void>;
};

export function usePlatformProvidersData(token: string): PlatformProvidersDataState {
  const { t } = useTranslation("common");
  const [state, setState] = useState<LoadState>("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [capabilities, setCapabilities] = useState<PlatformCapability[]>([]);
  const [providers, setProviders] = useState<PlatformProvider[]>([]);
  const [providerFamilies, setProviderFamilies] = useState<PlatformProviderFamily[]>([]);
  const [deployments, setDeployments] = useState<PlatformDeploymentProfile[]>([]);

  const reload = useCallback(async (): Promise<void> => {
    if (!token) {
      setState("error");
      setErrorMessage(t("platformControl.feedback.authRequired"));
      return;
    }

    setState("loading");
    setErrorMessage("");

    try {
      const [capabilitiesPayload, providersPayload, providerFamiliesPayload, deploymentsPayload] = await Promise.all([
        listPlatformCapabilities(token),
        listPlatformProviders(token),
        listPlatformProviderFamilies(token),
        listPlatformDeployments(token),
      ]);
      setCapabilities(capabilitiesPayload);
      setProviders(providersPayload);
      setProviderFamilies(providerFamiliesPayload);
      setDeployments(deploymentsPayload);
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
    providerFamilies,
    deployments,
    reload,
  };
}
