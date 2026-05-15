import { useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import type { CatalogMcpServer } from "../../../api/catalog";
import type { PageSubmenuItem } from "../../../components/navigation";
import { buildCatalogControlUrl, type CatalogControlSection, type CatalogMcpView } from "../routes";
import type { McpServerFormState } from "./useCatalogControl";

type UseMcpCatalogRouteStateInput = {
  activeSection: CatalogControlSection;
  activeMcpView: CatalogMcpView;
  activeMcpServerId: string;
  mcpServers: CatalogMcpServer[];
  mcpServerForm: McpServerFormState;
  openMcpEditor: (server: CatalogMcpServer) => void;
  resetMcpServerForm: () => void;
};

export function useMcpCatalogRouteState({
  activeSection,
  activeMcpView,
  activeMcpServerId,
  mcpServers,
  mcpServerForm,
  openMcpEditor,
  resetMcpServerForm,
}: UseMcpCatalogRouteStateInput): {
  selectedMcpServer: CatalogMcpServer | null;
  mcpSubmenuItems: PageSubmenuItem[];
} {
  const { t } = useTranslation("common");
  const selectedMcpServer = useMemo(
    () => mcpServers.find((server) => server.id === activeMcpServerId) ?? null,
    [activeMcpServerId, mcpServers],
  );

  useEffect(() => {
    if (activeSection !== "mcp" || activeMcpView !== "edit" || !selectedMcpServer) {
      return;
    }
    if (mcpServerForm.mcpServerId !== selectedMcpServer.id) {
      openMcpEditor(selectedMcpServer);
    }
  }, [activeMcpView, activeSection, mcpServerForm.mcpServerId, openMcpEditor, selectedMcpServer]);

  useEffect(() => {
    if (activeSection !== "mcp" || activeMcpView !== "create" || mcpServerForm.mode === "create") {
      return;
    }
    resetMcpServerForm();
  }, [activeMcpView, activeSection, mcpServerForm.mode, resetMcpServerForm]);

  const mcpSubmenuItems = useMemo(
    () => {
      const items: PageSubmenuItem[] = [
        {
          id: "mcp-registry",
          label: t("catalogControl.mcp.views.registry"),
          isActive: activeMcpView === "registry",
          to: buildCatalogControlUrl("mcp", "registry"),
        },
        {
          id: "create-mcp",
          label: t("catalogControl.mcp.views.create"),
          isActive: activeMcpView === "create",
          to: buildCatalogControlUrl("mcp", "create"),
        },
      ];
      if (selectedMcpServer) {
        items.push({
          id: "edit-mcp",
          label: t("catalogControl.mcp.views.edit", { name: selectedMcpServer.spec.name }),
          isActive: activeMcpView === "edit",
          to: buildCatalogControlUrl("mcp", "edit", { mcpServerId: selectedMcpServer.id }),
        });
      }
      return items;
    },
    [activeMcpView, selectedMcpServer, t],
  );

  return {
    selectedMcpServer,
    mcpSubmenuItems,
  };
}
