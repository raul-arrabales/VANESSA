import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router-dom";
import { useAuth } from "../../../auth/AuthProvider";
import PageSectionTabs from "../../../components/PageSectionTabs";
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
  const activeSection = MODEL_OPS_WORKSPACE_NAV_ITEMS.find((item) => (
    isModelOpsWorkspacePathActive(location.pathname, item.path)
  ))?.section ?? "overview";
  const tabItems = MODEL_OPS_WORKSPACE_NAV_ITEMS
    .filter((item) => canAccessModelOpsWorkspaceSection(user?.role, item.minimumRole))
    .map((item) => ({
      id: item.section,
      label: t(item.labelKey),
      to: item.path,
      isActive: isModelOpsWorkspacePathActive(location.pathname, item.path),
    }));

  return (
    <section className="card-stack modelops-workspace-layout">
      <article className="panel card-stack modelops-workspace-header-panel" data-modelops-section={activeSection}>
        <div className="platform-page-header">
          <div className="status-row">
            <p className="eyebrow">{t("modelOps.eyebrow")}</p>
            <h2 className="section-title">{t("modelOps.workspace.title")}</h2>
            <p className="status-text">
              {isSuperadmin ? t("modelOps.workspace.superadminDescription") : t("modelOps.workspace.description")}
            </p>
          </div>
        </div>
        <PageSectionTabs items={tabItems} ariaLabel={t("modelOps.workspace.navigationAria")} />
      </article>

      {children}
    </section>
  );
}
