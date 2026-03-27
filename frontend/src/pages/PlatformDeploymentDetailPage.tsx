import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";
import PlatformDeploymentAuditTable from "../features/platform-control/components/PlatformDeploymentAuditTable";
import PlatformDeploymentCloneSection from "../features/platform-control/components/PlatformDeploymentCloneSection";
import PlatformDeploymentDangerSection from "../features/platform-control/components/PlatformDeploymentDangerSection";
import PlatformDeploymentForm from "../features/platform-control/components/PlatformDeploymentForm";
import PlatformDeploymentOverviewSection from "../features/platform-control/components/PlatformDeploymentOverviewSection";
import PlatformPageLayout from "../features/platform-control/components/PlatformPageLayout";
import { usePlatformDeploymentDetail } from "../features/platform-control/hooks/usePlatformDeploymentDetail";

export default function PlatformDeploymentDetailPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const { deploymentId = "" } = useParams();
  const {
    activating,
    capabilityLabelByKey,
    cloneForm,
    cloning,
    confirmDelete,
    deployment,
    deploymentAudit,
    errorMessage,
    form,
    handleActivate,
    handleClone,
    handleDelete,
    handleSave,
    knowledgeBases,
    loadErrorMessage,
    modelResourcesByCapability,
    providersByCapability,
    requiredCapabilities,
    resetForm,
    saving,
    setCloneForm,
    setConfirmDelete,
    setForm,
    state,
  } = usePlatformDeploymentDetail({
    deploymentId,
    token,
  });

  return (
    <PlatformPageLayout
      title={deployment?.display_name ?? t("platformControl.deployments.detailTitle")}
      description={deployment ? t("platformControl.deployments.detailDescription") : t("platformControl.deployments.notFound")}
      errorMessage={errorMessage || loadErrorMessage}
      actions={(
        <Link className="btn btn-secondary" to="/control/platform/deployments">
          {t("platformControl.actions.viewDeployments")}
        </Link>
      )}
    >
      {state === "success" && !deployment ? (
        <article className="panel card-stack">
          <p className="status-text">{t("platformControl.deployments.notFound")}</p>
        </article>
      ) : null}

      {deployment ? (
        <>
          <PlatformDeploymentOverviewSection
            activating={activating}
            capabilityLabelByKey={capabilityLabelByKey}
            deployment={deployment}
            onActivate={() => void handleActivate()}
          />

          {form ? (
            <article className="panel card-stack">
              <div className="status-row">
                <h3 className="section-title">{t("platformControl.sections.settings")}</h3>
                <p className="status-text">{t("platformControl.deployments.settingsDescription")}</p>
              </div>
              <PlatformDeploymentForm
                value={form}
                capabilities={requiredCapabilities}
                providersByCapability={providersByCapability}
                modelResourcesByCapability={modelResourcesByCapability}
                knowledgeBases={knowledgeBases}
                helperText={t("platformControl.deployments.editing", { slug: deployment.slug })}
                isSubmitting={saving}
                submitLabel={t("platformControl.actions.saveDeployment")}
                submitBusyLabel={t("platformControl.actions.saving")}
                secondaryAction={{
                  label: t("platformControl.actions.reset"),
                  onClick: resetForm,
                }}
                onChange={setForm}
                onSubmit={(event) => {
                  event.preventDefault();
                  void handleSave();
                }}
              />
            </article>
          ) : null}

          {cloneForm ? (
            <PlatformDeploymentCloneSection
              cloneForm={cloneForm}
              cloning={cloning}
              onClone={() => void handleClone()}
              onCloneFormChange={setCloneForm}
            />
          ) : null}

          <PlatformDeploymentAuditTable
            entries={deploymentAudit}
            title={t("platformControl.deployments.recentActivations")}
            description={t("platformControl.deployments.recentActivationsDescription")}
          />

          <PlatformDeploymentDangerSection
            confirmDelete={confirmDelete}
            deploymentIsActive={deployment.is_active}
            onDelete={() => void handleDelete()}
            onToggleConfirmDelete={setConfirmDelete}
          />
        </>
      ) : null}
    </PlatformPageLayout>
  );
}
