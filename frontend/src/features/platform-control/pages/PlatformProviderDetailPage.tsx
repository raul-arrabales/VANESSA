import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../../../auth/AuthProvider";
import PlatformPageLayout from "../components/PlatformPageLayout";
import PlatformProviderDangerSection from "../components/PlatformProviderDangerSection";
import PlatformProviderForm from "../components/PlatformProviderForm";
import PlatformProviderLoadPanel from "../components/PlatformProviderLoadPanel";
import PlatformProviderLoadedModelSection from "../components/PlatformProviderLoadedModelSection";
import PlatformProviderOverviewSection from "../components/PlatformProviderOverviewSection";
import PlatformProviderUsagePanel from "../components/PlatformProviderUsagePanel";
import PlatformProviderValidationPanel from "../components/PlatformProviderValidationPanel";
import { usePlatformProviderDetail } from "../hooks/usePlatformProviderDetail";

export default function PlatformProviderDetailPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const { providerId = "" } = useParams();
  const {
    activeDeployment,
    capabilities,
    confirmDelete,
    credentialsLoading,
    deployments,
    dismissTrackedLoadPanel,
    errorMessage,
    form,
    handleAssignLoadedModel,
    handleClearLoadedModel,
    handleDelete,
    handleSubmit,
    handleValidate,
    isLoadPanelOpen,
    isUsedByActiveDeployment,
    loadDisplay,
    loadErrorMessage,
    loadPanelPhase,
    provider,
    providerFamily,
    providerFamilies,
    resetProviderForm,
    saving,
    setConfirmDelete,
    setForm,
    setSlotModelId,
    setValidationCredentialId,
    slotLoading,
    slotModelId,
    slotModels,
    state,
    supportsLocalSlot,
    supportsByokValidation,
    validating,
    validation,
    validationCredentialId,
    validationCredentials,
  } = usePlatformProviderDetail({
    providerId,
    token,
  });

  return (
    <PlatformPageLayout
      title={provider?.display_name ?? t("platformControl.providers.detailTitle")}
      description={provider ? t("platformControl.providers.detailDescription") : t("platformControl.providers.notFound")}
      errorMessage={errorMessage || loadErrorMessage}
      actions={(
        <Link className="btn btn-secondary" to="/control/platform/providers">
          {t("platformControl.actions.viewProviders")}
        </Link>
      )}
    >
      {state === "success" && !provider ? (
        <article className="panel card-stack">
          <p className="status-text">{t("platformControl.providers.notFound")}</p>
        </article>
      ) : null}

      {provider ? (
        <>
          <PlatformProviderOverviewSection
            activeDeployment={activeDeployment}
            isUsedByActiveDeployment={isUsedByActiveDeployment}
            provider={provider}
            providerFamily={providerFamily}
          />

          <PlatformProviderValidationPanel
            validation={validation}
            isValidating={validating}
            credentials={validationCredentials}
            credentialsLoading={credentialsLoading}
            selectedCredentialId={validationCredentialId}
            supportsByokValidation={supportsByokValidation}
            onCredentialChange={setValidationCredentialId}
            onValidate={() => void handleValidate()}
          />

          {supportsLocalSlot ? (
            <PlatformProviderLoadedModelSection
              loadDisplay={loadDisplay}
              onAssignLoadedModel={() => void handleAssignLoadedModel()}
              onClearLoadedModel={() => void handleClearLoadedModel()}
              onSlotModelChange={setSlotModelId}
              provider={provider}
              slotLoading={slotLoading}
              slotModelId={slotModelId}
              slotModels={slotModels}
            />
          ) : null}

          <PlatformProviderUsagePanel
            providerId={provider.id}
            capabilities={capabilities}
            deployments={deployments}
          />

          {form ? (
            <article className="panel card-stack">
              <div className="status-row">
                <h3 className="section-title">{t("platformControl.sections.settings")}</h3>
                <p className="status-text">{t("platformControl.providers.settingsDescription")}</p>
              </div>
              <PlatformProviderForm
                value={form}
                providerFamilies={providerFamilies}
                familyDisabled
                helperText={t("platformControl.providers.editing", { slug: provider.slug })}
                isSubmitting={saving}
                submitLabel={t("platformControl.actions.saveProvider")}
                submitBusyLabel={t("platformControl.actions.saving")}
                secondaryAction={{
                  label: t("platformControl.actions.reset"),
                  onClick: resetProviderForm,
                }}
                onChange={setForm}
                onSubmit={(event) => {
                  event.preventDefault();
                  void handleSubmit();
                }}
              />
            </article>
          ) : null}

          <PlatformProviderDangerSection
            confirmDelete={confirmDelete}
            onDelete={() => void handleDelete()}
            onToggleConfirmDelete={setConfirmDelete}
          />
        </>
      ) : null}

      {provider && supportsLocalSlot && isLoadPanelOpen && loadPanelPhase !== "idle" ? (
        <PlatformProviderLoadPanel
          providerDisplayName={provider.display_name}
          loadPanelPhase={loadPanelPhase}
          display={loadDisplay}
          onDismiss={dismissTrackedLoadPanel}
        />
      ) : null}
    </PlatformPageLayout>
  );
}
