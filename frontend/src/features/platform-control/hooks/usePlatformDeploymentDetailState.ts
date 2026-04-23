import { useEffect, useMemo, useRef, useState } from "react";
import type { Location } from "react-router-dom";
import type { TFunction } from "i18next";
import type { PlatformActivationAuditEntry, PlatformCapability, PlatformDeploymentProfile, PlatformProvider } from "../../../api/platform";
import type { KnowledgeBase } from "../../../api/context";
import type { ManagedModel } from "../../../api/modelops";
import { readDeploymentSeedFromState } from "../deploymentRouteState";
import { usePlatformDeploymentEditor } from "./usePlatformDeploymentEditor";
import { usePlatformDeploymentEditorData } from "./usePlatformDeploymentEditorData";
import type { DeploymentCloneFormState, DeploymentFormState } from "../deploymentEditor";

type UsePlatformDeploymentDetailStateParams = {
  deploymentId: string;
  token: string;
  location: Location;
  t: TFunction<"common">;
};

type UsePlatformDeploymentDetailStateResult = {
  state: ReturnType<typeof usePlatformDeploymentEditorData>["state"];
  loadErrorMessage: string;
  capabilities: PlatformCapability[];
  providers: PlatformProvider[];
  deployments: PlatformDeploymentProfile[];
  activationAudit: PlatformActivationAuditEntry[];
  eligibleModelsByCapability: Record<string, ManagedModel[]>;
  knowledgeBases: KnowledgeBase[];
  reload: () => Promise<void>;
  deployment: PlatformDeploymentProfile | null;
  deploymentAudit: PlatformActivationAuditEntry[];
  capabilityLabelByKey: Map<string, string>;
  requiredCapabilities: PlatformCapability[];
  providersByCapability: Record<string, PlatformProvider[]>;
  modelResourcesByCapability: Record<string, ManagedModel[]>;
  form: DeploymentFormState | null;
  setForm: React.Dispatch<React.SetStateAction<DeploymentFormState | null>>;
  cloneForm: DeploymentCloneFormState | null;
  setCloneForm: React.Dispatch<React.SetStateAction<DeploymentCloneFormState | null>>;
  setLocalDeployment: React.Dispatch<React.SetStateAction<PlatformDeploymentProfile | null>>;
  resetForm: () => void;
};

export function usePlatformDeploymentDetailState({
  deploymentId,
  token,
  location,
  t,
}: UsePlatformDeploymentDetailStateParams): UsePlatformDeploymentDetailStateResult {
  const {
    state,
    errorMessage: loadErrorMessage,
    capabilities,
    providers,
    deployments,
    activationAudit,
    eligibleModelsByCapability,
    knowledgeBases,
    reload,
  } = usePlatformDeploymentEditorData(token);
  const [form, setForm] = useState<DeploymentFormState | null>(null);
  const [cloneForm, setCloneForm] = useState<DeploymentCloneFormState | null>(null);
  const [localDeployment, setLocalDeployment] = useState<PlatformDeploymentProfile | null>(null);
  const seedReloadedDeploymentIdRef = useRef<string>("");
  const initializedDeploymentIdRef = useRef<string>("");

  const fetchedDeployment = deployments.find((item) => item.id === deploymentId) ?? null;
  const seededDeployment = readDeploymentSeedFromState(location.state, deploymentId);
  const deployment = localDeployment ?? fetchedDeployment ?? seededDeployment;
  const capabilityLabelByKey = useMemo(
    () => new Map(capabilities.map((capability) => [capability.capability, capability.display_name])),
    [capabilities],
  );
  const {
    capabilities: editorCapabilities,
    requiredCapabilities,
    providersByCapability,
    modelResourcesByCapability,
    buildInitialForm,
    buildInitialCloneForm,
  } = usePlatformDeploymentEditor({
    mode: "edit",
    capabilities,
    providers,
    eligibleModelsByCapability,
    knowledgeBases,
    deployment,
    t,
  });
  const deploymentAudit = activationAudit.filter((entry) => entry.deployment_profile.id === deploymentId);

  useEffect(() => {
    if (!deployment) {
      initializedDeploymentIdRef.current = "";
      return;
    }
    if (initializedDeploymentIdRef.current !== deployment.id) {
      initializedDeploymentIdRef.current = deployment.id;
      setForm(buildInitialForm());
      setCloneForm(buildInitialCloneForm());
    }
  }, [buildInitialCloneForm, buildInitialForm, deployment]);

  useEffect(() => {
    setLocalDeployment(null);
  }, [deploymentId]);

  useEffect(() => {
    if (!seededDeployment || fetchedDeployment) {
      seedReloadedDeploymentIdRef.current = "";
      return;
    }
    if (seedReloadedDeploymentIdRef.current === seededDeployment.id) {
      return;
    }

    seedReloadedDeploymentIdRef.current = seededDeployment.id;
    void reload();
  }, [fetchedDeployment, reload, seededDeployment]);

  return {
    state,
    loadErrorMessage,
    providers,
    deployments,
    activationAudit,
    eligibleModelsByCapability,
    knowledgeBases,
    reload,
    deployment,
    deploymentAudit,
    capabilityLabelByKey,
    requiredCapabilities,
    capabilities: editorCapabilities,
    providersByCapability,
    modelResourcesByCapability,
    form,
    setForm,
    cloneForm,
    setCloneForm,
    setLocalDeployment,
    resetForm: () => {
      if (deployment) {
        setForm(buildInitialForm());
      }
    },
  };
}
