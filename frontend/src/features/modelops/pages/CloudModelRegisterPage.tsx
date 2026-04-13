import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import PageSubmenuBar from "../../../components/PageSubmenuBar";
import type { ManagedModel } from "../../../api/modelops/types";
import { useAuth } from "../../../auth/AuthProvider";
import { ModelOpsWorkspaceFrame } from "../components/ModelOpsWorkspaceFrame";
import ModelCatalogList from "../components/ModelCatalogList";
import CloudCredentialList from "../components/CloudCredentialList";
import CloudCredentialForm from "../components/CloudCredentialForm";
import CloudModelRegistrationForm from "../components/CloudModelRegistrationForm";
import { CLOUD_PROVIDER_OPTIONS, TASK_OPTIONS } from "../domain";
import { useCloudRegistrationFlow } from "../hooks/useCloudRegistrationFlow";

type CredentialFormState = {
  provider: string;
  credentialScope: "platform" | "personal";
  displayName: string;
  apiBaseUrl: string;
  apiKey: string;
};

type CloudModelState = {
  id: string;
  name: string;
  provider: string;
  accessMode: "personal_private" | "platform_shared";
  providerModelId: string;
  credentialId: string;
  taskKey: string;
  comment: string;
};

type CloudModelRegisterView = "credentials" | "register" | "recent";

const CLOUD_MODEL_REGISTER_VIEW_ORDER: ReadonlyArray<CloudModelRegisterView> = [
  "credentials",
  "register",
  "recent",
];

function resolveCloudModelRegisterView(value: string | null): CloudModelRegisterView {
  if (value === "credentials" || value === "register" || value === "recent") {
    return value;
  }
  return "register";
}

function resolveCloudProvider(value: string | null): string {
  return CLOUD_PROVIDER_OPTIONS.some((option) => option.value === value) ? String(value) : "openai_compatible";
}

export default function CloudModelRegisterPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token, user } = useAuth();
  const {
    credentials,
    recentCloudModels,
    discoveredCloudModels,
    isLoading,
    isSaving,
    isDiscovering,
    clearCloudDiscovery,
    saveCredential,
    revokeCredential,
    discoverProviderModels,
    registerCloudModel,
  } =
    useCloudRegistrationFlow(token);
  const isSuperadmin = user?.role === "superadmin";
  const canTest = user?.role === "admin" || user?.role === "superadmin";
  const [lastRegisteredModelId, setLastRegisteredModelId] = useState("");
  const [searchParams, setSearchParams] = useSearchParams();
  const activeView = resolveCloudModelRegisterView(searchParams.get("view"));
  const requestedProvider = resolveCloudProvider(searchParams.get("provider"));
  const submenuItems = CLOUD_MODEL_REGISTER_VIEW_ORDER.map((view) => ({
    id: view,
    label: t(`modelOps.cloud.views.${view}`),
    isActive: activeView === view,
    onSelect: () => handleChangeView(view),
  }));

  const [credentialState, setCredentialState] = useState<CredentialFormState>({
    provider: requestedProvider,
    credentialScope: "personal" as const,
    displayName: "",
    apiBaseUrl: "https://api.openai.com/v1",
    apiKey: "",
  });

  const [modelState, setModelState] = useState<CloudModelState>({
    id: "",
    name: "",
    provider: "",
    accessMode: "personal_private" as const,
    providerModelId: "",
    credentialId: "",
    taskKey: "llm",
    comment: "",
  });

  const recentModels = useMemo(
    () => recentCloudModels as ManagedModel[],
    [recentCloudModels],
  );
  const selectedDiscoveredModel = useMemo(
    () => discoveredCloudModels.find((model) => model.provider_model_id === modelState.providerModelId) ?? null,
    [discoveredCloudModels, modelState.providerModelId],
  );

  useEffect(() => {
    if (activeView === "credentials") {
      setCredentialState((current) => ({ ...current, provider: requestedProvider }));
    }
  }, [activeView, requestedProvider]);

  function handleChangeView(view: CloudModelRegisterView): void {
    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.set("view", view);
    setSearchParams(nextSearchParams);
  }

  return (
    <ModelOpsWorkspaceFrame
      secondaryNavigation={<PageSubmenuBar items={submenuItems} ariaLabel={t("modelOps.cloud.views.aria")} />}
    >
      <section className="card-stack">
        {activeView === "credentials" ? (
          <>
            <CloudCredentialList
              credentials={credentials}
              isLoading={isLoading}
              isRevoking={isSaving}
              onRevoke={revokeCredential}
            />
            <CloudCredentialForm
              state={credentialState}
              isSaving={isSaving}
              canChoosePlatformScope={isSuperadmin}
              onChange={setCredentialState}
              onSubmit={async () => {
                await saveCredential({
                  provider: credentialState.provider,
                  display_name: credentialState.displayName.trim() || undefined,
                  api_base_url: credentialState.apiBaseUrl.trim() || undefined,
                  api_key: credentialState.apiKey,
                  credential_scope: isSuperadmin ? credentialState.credentialScope : "personal",
                });
                setCredentialState((current) => ({ ...current, displayName: "", apiKey: "" }));
              }}
            />
          </>
        ) : null}

        {activeView === "register" ? (
          <>
            <CloudModelRegistrationForm
              state={modelState}
              credentials={credentials}
              isLoading={isLoading}
              isSaving={isSaving}
              isDiscovering={isDiscovering}
              discoveredModels={discoveredCloudModels}
              allowPlatformOwnership={isSuperadmin}
              actorUserId={user?.id}
              onChange={setModelState}
              onDiscover={discoverProviderModels}
              onClearDiscovery={clearCloudDiscovery}
              onSubmit={async () => {
                const category = selectedDiscoveredModel?.category ?? TASK_OPTIONS.find((option) => option.value === modelState.taskKey)?.category ?? "generative";
                const accessMode = isSuperadmin ? modelState.accessMode : "personal_private";
                const ownerType = accessMode === "platform_shared" ? "platform" : "user";
                const created = await registerCloudModel({
                  id: modelState.id.trim(),
                  name: modelState.name.trim(),
                  provider: modelState.provider,
                  owner_type: ownerType,
                  visibility_scope: ownerType === "platform" ? "platform" : "private",
                  provider_model_id: modelState.providerModelId.trim(),
                  credential_id: modelState.credentialId || undefined,
                  task_key: modelState.taskKey,
                  category,
                  source_id: modelState.providerModelId.trim(),
                  metadata: {
                    provider_discovery: {
                      provider: modelState.provider,
                      provider_model_id: selectedDiscoveredModel?.provider_model_id ?? modelState.providerModelId.trim(),
                      name: selectedDiscoveredModel?.name ?? modelState.name.trim(),
                      owned_by: selectedDiscoveredModel?.owned_by ?? null,
                      created_at: selectedDiscoveredModel?.created_at ?? null,
                      task_key: modelState.taskKey,
                      category,
                      metadata: selectedDiscoveredModel?.metadata ?? {},
                    },
                  },
                  comment: modelState.comment.trim() || undefined,
                });
                setLastRegisteredModelId(created?.id ?? "");
                clearCloudDiscovery();
                setModelState({
                  id: "",
                  name: "",
                  provider: "",
                  accessMode: "personal_private",
                  providerModelId: "",
                  credentialId: "",
                  taskKey: "llm",
                  comment: "",
                });
              }}
            />

            {lastRegisteredModelId && (
              <div className="button-row">
                <Link
                  className="btn btn-secondary"
                  to={
                    canTest
                      ? `/control/models/${encodeURIComponent(lastRegisteredModelId)}/test`
                      : `/control/models/${encodeURIComponent(lastRegisteredModelId)}`
                  }
                >
                  {canTest ? t("modelOps.actions.testModel") : t("modelOps.actions.openDetail")}
                </Link>
              </div>
            )}
          </>
        ) : null}

        {activeView === "recent" ? (
          <article className="panel card-stack">
            <h2 className="section-title">{t("modelOps.cloud.recentTitle")}</h2>
            {isLoading ? (
              <p className="status-text">{t("modelOps.states.loading")}</p>
            ) : (
              <ModelCatalogList
                models={recentModels}
                emptyLabel={t("modelOps.cloud.emptyRecent")}
                detailLabel={t("modelOps.actions.openDetail")}
                validatedLabel={t("modelOps.catalog.validatedBadge")}
                notValidatedLabel={t("modelOps.catalog.notValidatedBadge")}
              />
            )}
          </article>
        ) : null}
      </section>
    </ModelOpsWorkspaceFrame>
  );
}
