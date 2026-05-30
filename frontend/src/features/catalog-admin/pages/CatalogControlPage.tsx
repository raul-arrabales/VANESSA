import { useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import PageSubmenuBar from "../../../components/PageSubmenuBar";
import { useAuth } from "../../../auth/AuthProvider";
import CatalogAgentsDirectory from "../components/CatalogAgentsDirectory";
import CatalogMcpRegistry from "../components/CatalogMcpRegistry";
import CatalogMcpServerFormPanel from "../components/CatalogMcpServerFormPanel";
import CatalogOverviewSection from "../components/CatalogOverviewSection";
import CatalogPageLayout from "../components/CatalogPageLayout";
import CatalogToolFormPanel from "../components/CatalogToolFormPanel";
import CatalogToolTestPanel from "../components/CatalogToolTestPanel";
import CatalogToolsDirectory from "../components/CatalogToolsDirectory";
import CatalogUserAgentBuilderPanel from "../components/CatalogUserAgentBuilderPanel";
import CatalogUserAgentsDirectory from "../components/CatalogUserAgentsDirectory";
import { useCatalogControl } from "../hooks/useCatalogControl";
import { useMcpCatalogRouteState } from "../hooks/useMcpCatalogRouteState";
import { useUserAgentProjectsControl } from "../hooks/useUserAgentProjectsControl";
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
  const { token } = useAuth();
  const navigate = useNavigate();
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
    toolForm,
    setToolForm,
    toolCreationOptions,
    mcpCreationOptions,
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
    testingToolId,
    savingTool,
    savingMcpServer,
    loadCatalogState,
    handleAgentValidate,
    handleToolValidate,
    handleMcpValidate,
    handleToolSubmit,
    handleMcpSubmit,
    handleMcpDelete,
    handleMcpToggle,
    handleToolTest,
    openAgentEditor,
    openToolEditor,
    openMcpEditor,
    openToolTester,
    resetToolForm,
    resetMcpServerForm,
    publishedAgents,
    publishedTools,
    enabledMcpServers,
  } = useCatalogControl(token);
  const allCatalogAgentNames = useMemo(
    () => agents.map((agent) => agent.spec.name),
    [agents],
  );
  const {
    projects: userAgentProjects,
    loading: userAgentProjectsLoading,
    saving: userAgentProjectSaving,
    validatingProjectId,
    publishingProjectId,
    form: userAgentForm,
    setForm: setUserAgentForm,
    validations: userAgentValidations,
    selectProject,
    setCreateAgentType,
    resetForm: resetUserAgentForm,
    submitForm,
    validateProject,
    publishProject,
  } = useUserAgentProjectsControl(token, allCatalogAgentNames);
  const selectedTestTool = tools.find((tool) => tool.id === activeToolId) ?? null;
  const platformAgents = useMemo(
    () => agents.filter((agent) => agent.is_platform_agent || agent.agent_kind === "platform"),
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
          agents={agents}
          agentValidationResults={agentValidationResults}
          agentCount={agents.length}
          publishedAgents={publishedAgents}
          toolCount={tools.length}
          publishedTools={publishedTools}
          tools={tools}
          mcpServers={mcpServers}
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
          toolCreationOptions={toolCreationOptions}
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
          deletingAgentId=""
          onValidate={(agentId) => void handleAgentValidate(agentId)}
          onEdit={(agent) => {
            openAgentEditor(agent);
            navigate(buildCatalogControlUrl("agents", "create"));
          }}
        />
      ) : null}

      {activeSection === "agents" && activeAgentsView === "user-agents" ? (
        <CatalogUserAgentsDirectory
          projects={userAgentProjects}
          loading={userAgentProjectsLoading}
          validatingProjectId={validatingProjectId}
          publishingProjectId={publishingProjectId}
          validations={userAgentValidations}
          onEdit={(project) => {
            selectProject(project);
            navigate(buildCatalogControlUrl("agents", "create"));
          }}
          onValidate={(projectId) => void validateProject(projectId)}
          onPublish={(projectId) => void publishProject(projectId)}
        />
      ) : null}

      {activeSection === "agents" && activeAgentsView === "create" ? (
        <CatalogUserAgentBuilderPanel
          form={userAgentForm}
          mcpServers={mcpServers}
          models={models}
          saving={userAgentProjectSaving}
          onChange={setUserAgentForm}
          onAgentTypeChange={setCreateAgentType}
          onSubmit={(event) => {
            event.preventDefault();
            void submitForm();
          }}
          onReset={resetUserAgentForm}
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
          mcpCreationOptions={mcpCreationOptions}
          saving={savingMcpServer}
          onChange={setMcpServerForm}
          onSubmit={(event) => {
            event.preventDefault();
            void handleMcpSubmit();
          }}
        />
      ) : null}
    </CatalogPageLayout>
  );
}
