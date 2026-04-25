import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import ModalDialog from "../../../components/ModalDialog";
import PageSubmenuBar from "../../../components/PageSubmenuBar";
import { useAuth } from "../../../auth/AuthProvider";
import type { CatalogAgent } from "../../../api/catalog";
import CatalogAgentFormPanel from "../components/CatalogAgentFormPanel";
import CatalogAgentsDirectory from "../components/CatalogAgentsDirectory";
import CatalogOverviewSection from "../components/CatalogOverviewSection";
import CatalogPageLayout from "../components/CatalogPageLayout";
import CatalogToolFormPanel from "../components/CatalogToolFormPanel";
import CatalogToolTestPanel from "../components/CatalogToolTestPanel";
import CatalogToolsDirectory from "../components/CatalogToolsDirectory";
import { useCatalogControl } from "../hooks/useCatalogControl";
import {
  buildCatalogControlUrl,
  resolveCatalogAgentsView,
  resolveCatalogControlSection,
  resolveCatalogToolId,
  resolveCatalogToolsView,
} from "../routes";

export default function CatalogControlPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { token, user } = useAuth();
  const navigate = useNavigate();
  const deleteConfirmButtonRef = useRef<HTMLButtonElement>(null);
  const [agentPendingDelete, setAgentPendingDelete] = useState<CatalogAgent | null>(null);
  const [searchParams] = useSearchParams();
  const activeSection = resolveCatalogControlSection(searchParams.get("section"));
  const activeToolsView = resolveCatalogToolsView(searchParams.get("view"));
  const activeAgentsView = resolveCatalogAgentsView(searchParams.get("view"));
  const activeToolId = resolveCatalogToolId(searchParams.get("toolId"));
  const {
    state,
    errorMessage,
    agents,
    tools,
    models,
    agentForm,
    setAgentForm,
    toolForm,
    setToolForm,
    toolTestForm,
    setToolTestForm,
    agentValidationResults,
    toolValidationResults,
    toolTestResult,
    toolTestError,
    validatingAgentId,
    validatingToolId,
    deletingAgentId,
    testingToolId,
    savingAgent,
    savingTool,
    loadCatalogState,
    handleAgentValidate,
    handleAgentDelete,
    handleToolValidate,
    handleAgentSubmit,
    handleToolSubmit,
    handleToolTest,
    openAgentEditor,
    openToolEditor,
    openToolTester,
    resetAgentForm,
    resetToolForm,
    publishedAgents,
    publishedTools,
  } = useCatalogControl(token);
  const selectedTestTool = tools.find((tool) => tool.id === activeToolId) ?? null;
  const platformAgents = useMemo(
    () => agents.filter((agent) => agent.is_platform_agent || agent.agent_kind === "platform"),
    [agents],
  );
  const userAgents = useMemo(
    () => agents.filter((agent) => !(agent.is_platform_agent || agent.agent_kind === "platform")),
    [agents],
  );
  const canDeleteAgent = (agent: CatalogAgent): boolean => {
    if (agent.is_platform_agent || agent.agent_kind === "platform") {
      return false;
    }
    return user?.role === "superadmin" || Number(agent.entity.owner_user_id) === Number(user?.id);
  };

  useEffect(() => {
    if (activeSection !== "tools" || activeToolsView !== "test" || !selectedTestTool) {
      return;
    }
    if (toolTestForm.toolId !== selectedTestTool.id) {
      openToolTester(selectedTestTool);
    }
  }, [activeSection, activeToolsView, openToolTester, selectedTestTool, toolTestForm.toolId]);

  const toolsSubmenuItems = useMemo(
    () => {
      const items = [
        {
          id: "platform-tools",
          label: t("catalogControl.tools.views.tools"),
          isActive: activeToolsView === "tools",
          to: buildCatalogControlUrl("tools", "tools"),
        },
        {
          id: "create-tool",
          label: t("catalogControl.tools.views.create"),
          isActive: activeToolsView === "create",
          to: buildCatalogControlUrl("tools", "create"),
        },
      ];
      if (selectedTestTool) {
        items.push({
          id: "test-tool",
          label: selectedTestTool.spec.name,
          isActive: activeToolsView === "test",
          to: buildCatalogControlUrl("tools", "test", { toolId: selectedTestTool.id }),
        });
      }
      return items;
    },
    [activeToolsView, selectedTestTool, t],
  );
  const agentsSubmenuItems = useMemo(
    () => [
      {
        id: "platform-agents",
        label: t("catalogControl.agents.views.agents"),
        isActive: activeAgentsView === "agents",
        to: buildCatalogControlUrl("agents", "agents"),
      },
      {
        id: "user-agents",
        label: t("catalogControl.agents.views.userAgents"),
        isActive: activeAgentsView === "user-agents",
        to: buildCatalogControlUrl("agents", "user-agents"),
      },
      {
        id: "create-agent",
        label: t("catalogControl.agents.views.create"),
        isActive: activeAgentsView === "create",
        to: buildCatalogControlUrl("agents", "create"),
      },
    ],
    [activeAgentsView, t],
  );

  const pageTitle = activeSection === "tools"
    ? t("catalogControl.tools.title")
    : activeSection === "agents"
      ? t("catalogControl.agents.title")
      : t("catalogControl.title");
  const pageDescription = activeSection === "tools"
    ? t("catalogControl.tools.pageDescription")
    : activeSection === "agents"
      ? t("catalogControl.agents.pageDescription")
      : t("catalogControl.home.description");
  const secondaryNavigation = activeSection === "tools"
    ? <PageSubmenuBar items={toolsSubmenuItems} ariaLabel={t("catalogControl.tools.views.aria")} />
    : activeSection === "agents"
      ? <PageSubmenuBar items={agentsSubmenuItems} ariaLabel={t("catalogControl.agents.views.aria")} />
      : undefined;

  return (
    <CatalogPageLayout
      activeSection={activeSection}
      title={pageTitle}
      description={pageDescription}
      errorMessage={errorMessage}
      secondaryNavigation={secondaryNavigation}
      actions={(
        <button type="button" className="btn btn-primary" onClick={() => void loadCatalogState()} disabled={state === "loading"}>
          {state === "loading" ? t("catalogControl.actions.refreshing") : t("catalogControl.actions.refresh")}
        </button>
      )}
    >
      {activeSection === "overview" ? (
        <CatalogOverviewSection
          state={state}
          agentCount={agents.length}
          publishedAgents={publishedAgents}
          toolCount={tools.length}
          publishedTools={publishedTools}
          modelCount={models.length}
        />
      ) : null}

      {activeSection === "tools" && activeToolsView === "tools" ? (
        <CatalogToolsDirectory
          tools={tools}
          validationResults={toolValidationResults}
          validatingToolId={validatingToolId}
          onValidate={(toolId) => void handleToolValidate(toolId)}
          onEdit={(tool) => {
            openToolEditor(tool);
            navigate(buildCatalogControlUrl("tools", "create"));
          }}
          onTest={(tool) => {
            openToolTester(tool);
            navigate(buildCatalogControlUrl("tools", "test", { toolId: tool.id }));
          }}
        />
      ) : null}

      {activeSection === "tools" && activeToolsView === "create" ? (
        <CatalogToolFormPanel
          form={toolForm}
          saving={savingTool}
          onChange={setToolForm}
          onSubmit={(event) => {
            event.preventDefault();
            void handleToolSubmit();
          }}
          onReset={resetToolForm}
        />
      ) : null}

      {activeSection === "tools" && activeToolsView === "test" ? (
        <CatalogToolTestPanel
          tool={selectedTestTool}
          form={toolTestForm}
          testing={testingToolId === toolTestForm.toolId}
          errorMessage={toolTestError}
          result={toolTestResult}
          onChange={setToolTestForm}
          onSubmit={() => void handleToolTest()}
        />
      ) : null}

      {activeSection === "agents" && activeAgentsView === "agents" ? (
        <CatalogAgentsDirectory
          agents={platformAgents}
          title={t("catalogControl.agents.platformListTitle")}
          description={t("catalogControl.agents.platformDescription")}
          emptyMessage={t("catalogControl.agents.emptyPlatform")}
          validationResults={agentValidationResults}
          validatingAgentId={validatingAgentId}
          deletingAgentId={deletingAgentId}
          onValidate={(agentId) => void handleAgentValidate(agentId)}
          onEdit={(agent) => {
            openAgentEditor(agent);
            navigate(buildCatalogControlUrl("agents", "create"));
          }}
        />
      ) : null}

      {activeSection === "agents" && activeAgentsView === "user-agents" ? (
        <CatalogAgentsDirectory
          agents={userAgents}
          title={t("catalogControl.agents.userListTitle")}
          description={t("catalogControl.agents.userDescription")}
          emptyMessage={t("catalogControl.agents.emptyUser")}
          validationResults={agentValidationResults}
          validatingAgentId={validatingAgentId}
          deletingAgentId={deletingAgentId}
          onValidate={(agentId) => void handleAgentValidate(agentId)}
          onEdit={(agent) => {
            openAgentEditor(agent);
            navigate(buildCatalogControlUrl("agents", "create"));
          }}
          onDelete={(agent) => {
            if (canDeleteAgent(agent)) {
              setAgentPendingDelete(agent);
            }
          }}
        />
      ) : null}

      {activeSection === "agents" && activeAgentsView === "create" ? (
        <CatalogAgentFormPanel
          form={agentForm}
          tools={tools}
          models={models}
          saving={savingAgent}
          onChange={setAgentForm}
          onSubmit={(event) => {
            event.preventDefault();
            void handleAgentSubmit();
          }}
          onReset={resetAgentForm}
        />
      ) : null}
      {agentPendingDelete ? (
        <ModalDialog
          title={t("catalogControl.agents.deleteDialog.title")}
          description={t("catalogControl.agents.deleteDialog.message", { name: agentPendingDelete.spec.name })}
          closeDisabled={Boolean(deletingAgentId)}
          onClose={() => {
            if (!deletingAgentId) {
              setAgentPendingDelete(null);
            }
          }}
          initialFocusRef={deleteConfirmButtonRef}
          actions={(
            <>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setAgentPendingDelete(null)}
                disabled={Boolean(deletingAgentId)}
              >
                {t("catalogControl.agents.deleteDialog.cancel")}
              </button>
              <button
                ref={deleteConfirmButtonRef}
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  void handleAgentDelete(agentPendingDelete).then((deleted) => {
                    if (deleted) {
                      setAgentPendingDelete(null);
                    }
                  });
                }}
                disabled={Boolean(deletingAgentId)}
              >
                {deletingAgentId ? t("catalogControl.actions.deleting") : t("catalogControl.agents.deleteDialog.confirm")}
              </button>
            </>
          )}
        />
      ) : null}
    </CatalogPageLayout>
  );
}
