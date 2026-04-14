import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import PageSubmenuBar from "../../../components/PageSubmenuBar";
import { useAuth } from "../../../auth/AuthProvider";
import PlatformDeploymentAuditTable from "../components/PlatformDeploymentAuditTable";
import PlatformDeploymentActivationDialog from "../components/PlatformDeploymentActivationDialog";
import PlatformDeploymentCloneSection from "../components/PlatformDeploymentCloneSection";
import PlatformDeploymentDangerSection from "../components/PlatformDeploymentDangerSection";
import PlatformDeploymentForm from "../components/PlatformDeploymentForm";
import PlatformDeploymentOverviewSection from "../components/PlatformDeploymentOverviewSection";
import PlatformPageLayout from "../components/PlatformPageLayout";
import { usePlatformDeploymentDetail } from "../hooks/usePlatformDeploymentDetail";

export default function PlatformDeploymentDetailPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token } = useAuth();
  const { deploymentId = "" } = useParams();
  const {
    activating,
    capabilityLabelByKey,
    cloneForm,
    cloning,
    confirmActivate,
    confirmDelete,
    deployment,
    deploymentAudit,
    deployments,
    errorMessage,
    form,
    handleActivate,
    handleClone,
    handleDelete,
    handleSaveCapability,
    handleSaveIdentity,
    knowledgeBases,
    loadErrorMessage,
    modelResourcesByCapability,
    providersByCapability,
    requiredCapabilities,
    resetForm,
    savingCapabilityKeys,
    savingIdentity,
    setCloneForm,
    setConfirmActivate,
    setConfirmDelete,
    setForm,
    state,
  } = usePlatformDeploymentDetail({
    deploymentId,
    token,
  });
  const activeDeployment = deployments.find((item) => item.is_active) ?? null;
  const deploymentViewLabel = deployment
    ? t("platformControl.deployments.views.deploymentDetail", { name: deployment.display_name })
    : t("platformControl.deployments.detailTitle");
  const submenuItems = [
    {
      id: "profiles",
      label: t("platformControl.deployments.views.profiles"),
      isActive: false,
      to: "/control/platform/deployments",
    },
    {
      id: "history",
      label: t("platformControl.deployments.views.history"),
      isActive: false,
      to: "/control/platform/deployments?view=history",
    },
    {
      id: "create",
      label: t("platformControl.deployments.views.create"),
      isActive: false,
      to: "/control/platform/deployments?view=create",
    },
    {
      id: "deployment-detail",
      label: deploymentViewLabel,
      isActive: true,
      to: deployment ? `/control/platform/deployments/${deployment.id}` : undefined,
    },
  ];

  return (
    <PlatformPageLayout
      title={deployment?.display_name ?? t("platformControl.deployments.detailTitle")}
      description={deployment ? t("platformControl.deployments.detailDescription") : t("platformControl.deployments.notFound")}
      errorMessage={errorMessage || loadErrorMessage}
      secondaryNavigation={<PageSubmenuBar items={submenuItems} ariaLabel={t("platformControl.deployments.views.aria")} />}
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
            onActivate={() => setConfirmActivate(true)}
          />

          {confirmActivate && !deployment.is_active ? (
            <PlatformDeploymentActivationDialog
              activeDeployment={activeDeployment}
              deployment={deployment}
              isPending={activating}
              onCancel={() => setConfirmActivate(false)}
              onConfirm={() => {
                setConfirmActivate(false);
                void handleActivate();
              }}
            />
          ) : null}

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
                bindingStatusByCapability={Object.fromEntries(
                  deployment.bindings.map((binding) => [binding.capability, binding.configuration_status]),
                )}
                helperText={t("platformControl.deployments.editing", { slug: deployment.slug })}
                identityAction={{
                  label: t("platformControl.actions.saveDeploymentIdentity"),
                  busyLabel: t("platformControl.actions.saving"),
                  isSubmitting: savingIdentity,
                  onClick: () => void handleSaveIdentity(),
                }}
                capabilityAction={{
                  label: t("platformControl.actions.saveBinding"),
                  busyLabel: t("platformControl.actions.saving"),
                  savingByCapability: savingCapabilityKeys,
                  onClick: (capability) => void handleSaveCapability(capability),
                }}
                secondaryAction={{
                  label: t("platformControl.actions.reset"),
                  onClick: resetForm,
                }}
                onChange={setForm}
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
