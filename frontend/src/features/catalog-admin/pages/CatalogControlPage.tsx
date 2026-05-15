import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import ModalDialog from "../../../components/ModalDialog";
import PageSubmenuBar from "../../../components/PageSubmenuBar";
import { useAuth } from "../../../auth/AuthProvider";
import type { CatalogAgent } from "../../../api/catalog";
import CatalogAgentFormPanel from "../components/CatalogAgentFormPanel";
import CatalogAgentsDirectory from "../components/CatalogAgentsDirectory";
import CatalogMcpRegistry from "../components/CatalogMcpRegistry";
import CatalogMcpServerFormPanel from "../components/CatalogMcpServerFormPanel";
import CatalogOverviewSection from "../components/CatalogOverviewSection";
import CatalogPageLayout from "../components/CatalogPageLayout";
import CatalogToolFormPanel from "../components/CatalogToolFormPanel";
import CatalogToolTestPanel from "../components/CatalogToolTestPanel";
import CatalogToolsDirectory from "../components/CatalogToolsDirectory";
import { useCatalogControl } from "../hooks/useCatalogControl";
import { useMcpCatalogRouteState } from "../hooks/useMcpCatalogRouteState";
import {
  buildCatalogControlUrl,
  resolveCatalogAgentsView,
  resolveCatalogControlSection,
  resolveCatalogMcpServerId,
  resolveCatalogMcpView,
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
  const activeMcpView = resolveCatalogMcpView(searchParams.get("view"));
  const activeToolId = resolveCatalogToolId(searchParams.get("toolId"));
  const activeMcpServerId = resolveCatalogMcpServerId(searchParams.get("id"));
  const {
    state,
    errorMessage,
    agents,
    tools,
    mcpServers,
    models,
    agentForm,
    setAgentForm,
    toolForm,
    setToolForm,
    mcpServerForm,
    setMcpServerForm,
    toolTestForm,
    setToolTestForm,
    agentValidationResults,
    toolValidationResults,
    mcpValidationResults,
    toolTestResult,
    toolTestError,
    validatingAgentId,
    validatingToolId,
    validatingMcpServerId,
    deletingAgentId,
    agentPromptPreview,
    agentPromptPreviewLoading,
    testingToolId,
    savingAgent,
    savingTool,
    savingMcpServer,
    loadCatalogState,
    handleAgentValidate,
    handleAgentDelete,
    handleToolValidate,
    handleMcpValidate,
    handleAgentSubmit,
    handleToolSubmit,
    handleMcpSubmit,
    handleMcpDelete,
    handleMcpToggle,
    handleToolTest,
    openAgentEditor,
    openToolEditor,
    openMcpEditor,
    openToolTester,
    resetAgentForm,
    resetToolForm,
    resetMcpServerForm,
    publishedAgents,
    publishedTools,
    enabledMcpServers,
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
  const {
    selectedMcpServer,
    mcpSubmenuItems,
  } = useMcpCatalogRouteState({
    activeSection,
    activeMcpView,
    activeMcpServerId,
    mcpServers,
    mcpServerForm,
    openMcpEditor,
    resetMcpServerForm,
  });
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
      : activeSection === "mcp"
        ? t("catalogControl.mcp.title")
      : t("catalogControl.title");
  const pageDescription = activeSection === "tools"
    ? t("catalogControl.tools.pageDescription")
    : activeSection === "agents"
      ? t("catalogControl.agents.pageDescription")
      : activeSection === "mcp"
        ? t("catalogControl.mcp.pageDescription")
      : t("catalogControl.home.description");
  const secondaryNavigation = activeSection === "tools"
    ? <PageSubmenuBar items={toolsSubmenuItems} ariaLabel={t("catalogControl.tools.views.aria")} />
    : activeSection === "agents"
      ? <PageSubmenuBar items={agentsSubmenuItems} ariaLabel={t("catalogControl.agents.views.aria")} />
      : activeSection === "mcp"
        ? <PageSubmenuBar items={mcpSubmenuItems} ariaLabel={t("catalogControl.mcp.views.aria")} />
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
          mcpServerCount={mcpServers.length}
          enabledMcpServers={enabledMcpServers}
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
          mcpServers={mcpServers}
          models={models}
          saving={savingAgent}
          promptPreview={agentPromptPreview}
          promptPreviewLoading={agentPromptPreviewLoading}
          onChange={setAgentForm}
          onSubmit={(event) => {
            event.preventDefault();
            void handleAgentSubmit();
          }}
          onReset={resetAgentForm}
        />
      ) : null}

      {activeSection === "mcp" && activeMcpView === "registry" ? (
        <CatalogMcpRegistry
          mcpServers={mcpServers}
          tools={tools}
          validationResults={mcpValidationResults}
          validatingMcpServerId={validatingMcpServerId}
          onEdit={(server) => {
            openMcpEditor(server);
            navigate(buildCatalogControlUrl("mcp", "edit", { mcpServerId: server.id }));
          }}
          onDelete={(server) => void handleMcpDelete(server)}
          onToggle={(server) => void handleMcpToggle(server)}
          onValidate={(serverId) => void handleMcpValidate(serverId)}
        />
      ) : null}

      {activeSection === "mcp" && (activeMcpView === "create" || activeMcpView === "edit") ? (
        <CatalogMcpServerFormPanel
          form={activeMcpView === "edit" && selectedMcpServer ? mcpServerForm : mcpServerForm}
          tools={tools}
          mcpServers={mcpServers}
          saving={savingMcpServer}
          onChange={setMcpServerForm}
          onSubmit={(event) => {
            event.preventDefault();
            void handleMcpSubmit();
          }}
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
