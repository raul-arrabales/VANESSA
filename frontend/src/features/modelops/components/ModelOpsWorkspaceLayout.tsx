import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router-dom";
import { useAuth } from "../../../auth/AuthProvider";
import TabbedWorkspaceLayout from "../../../components/TabbedWorkspaceLayout";
import {
  canAccessModelOpsWorkspaceSection,
  isModelOpsWorkspacePathActive,
  MODEL_OPS_WORKSPACE_NAV_ITEMS,
} from "../routes";

type ModelOpsWorkspaceLayoutProps = {
  children: ReactNode;
};

export function ModelOpsWorkspaceLayout({ children }: ModelOpsWorkspaceLayoutProps): JSX.Element {
  const { t } = useTranslation("common");
  const { user } = useAuth();
  const location = useLocation();
  const isSuperadmin = user?.role === "superadmin";
  const tabItems = MODEL_OPS_WORKSPACE_NAV_ITEMS
    .filter((item) => canAccessModelOpsWorkspaceSection(user?.role, item.minimumRole))
    .map((item) => ({
      id: item.section,
      label: t(item.labelKey),
      to: item.path,
      isActive: isModelOpsWorkspacePathActive(location.pathname, item.path),
    }));

  return (
    <TabbedWorkspaceLayout
      eyebrow={t("modelOps.eyebrow")}
      title={t("modelOps.workspace.title")}
      description={isSuperadmin ? t("modelOps.workspace.superadminDescription") : t("modelOps.workspace.description")}
      tabs={tabItems}
      ariaLabel={t("modelOps.workspace.navigationAria")}
    >
      {children}
    </TabbedWorkspaceLayout>
  );
}
