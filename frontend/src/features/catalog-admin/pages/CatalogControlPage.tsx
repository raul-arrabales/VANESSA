import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import PageSubmenuBar from "../../../components/PageSubmenuBar";
import { useAuth } from "../../../auth/AuthProvider";
import CatalogAgentFormPanel from "../components/CatalogAgentFormPanel";
import CatalogAgentsDirectory from "../components/CatalogAgentsDirectory";
import CatalogOverviewSection from "../components/CatalogOverviewSection";
import CatalogPageLayout from "../components/CatalogPageLayout";
import CatalogToolFormPanel from "../components/CatalogToolFormPanel";
import CatalogToolsDirectory from "../components/CatalogToolsDirectory";
import { useCatalogControl } from "../hooks/useCatalogControl";
import {
  buildCatalogControlUrl,
  resolveCatalogAgentsView,
  resolveCatalogControlSection,
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
    agentValidationResults,
    toolValidationResults,
    validatingAgentId,
    validatingToolId,
    savingAgent,
    savingTool,
    loadCatalogState,
    handleAgentValidate,
    handleToolValidate,
    handleAgentSubmit,
    handleToolSubmit,
    openAgentEditor,
    openToolEditor,
    resetAgentForm,
    resetToolForm,
    publishedAgents,
    publishedTools,
  } = useCatalogControl(token);

  const toolsSubmenuItems = useMemo(
    () => [
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
    ],
    [activeToolsView, t],
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

      {activeSection === "agents" && activeAgentsView === "agents" ? (
        <CatalogAgentsDirectory
          agents={agents}
          validationResults={agentValidationResults}
          validatingAgentId={validatingAgentId}
          onValidate={(agentId) => void handleAgentValidate(agentId)}
          onEdit={(agent) => {
            openAgentEditor(agent);
            navigate(buildCatalogControlUrl("agents", "create"));
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
    </CatalogPageLayout>
  );
}
