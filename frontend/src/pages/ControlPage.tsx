import { useTranslation } from "react-i18next";
import OptionCardGrid, { type OptionCardItem } from "../components/OptionCardGrid";
import { useAuth } from "../auth/AuthProvider";
import { hasRequiredRole } from "../auth/roles";
import type { Role } from "../auth/types";

type ControlItem = OptionCardItem & {
  minimumRole: Role;
};

export default function ControlPage(): JSX.Element {
  const { t } = useTranslation("common");
  const { user } = useAuth();
  const currentRole = user?.role ?? "user";
  const displayName = user?.username ?? user?.email ?? t("app.title");

  const items: ControlItem[] = [
    {
      id: "models",
      title: t("control.items.models.title"),
      description: t("control.items.models.description"),
      to: "/control/models",
      icon: "models",
      minimumRole: "user",
    },
    {
      id: "ai",
      title: t("control.items.ai.title"),
      description: t("control.items.ai.description"),
      to: "/ai",
      icon: "ai",
      minimumRole: "user",
    },
    {
      id: "quotes",
      title: t("control.items.quotes.title"),
      description: t("control.items.quotes.description"),
      to: "/control/quotes",
      icon: "approvals",
      minimumRole: "admin",
    },
    {
      id: "context",
      title: t("control.items.context.title"),
      description: t("control.items.context.description"),
      to: "/control/context",
      icon: "models",
      minimumRole: "admin",
    },
    {
      id: "approvals",
      title: t("control.items.approvals.title"),
      description: t("control.items.approvals.description"),
      to: "/control/approvals",
      icon: "approvals",
      minimumRole: "admin",
    },
    {
      id: "system-health",
      title: t("control.items.systemHealth.title"),
      description: t("control.items.systemHealth.description"),
      to: "/control/system-health",
      icon: "health",
      minimumRole: "superadmin",
    },
    {
      id: "platform",
      title: t("control.items.platform.title"),
      description: t("control.items.platform.description"),
      to: "/control/platform",
      icon: "adminPage",
      minimumRole: "superadmin",
    },
    {
      id: "catalog",
      title: t("control.items.catalog.title"),
      description: t("control.items.catalog.description"),
      to: "/control/catalog",
      icon: "models",
      minimumRole: "superadmin",
    },
  ];

  const visibleItems = items.filter((item) => hasRequiredRole(currentRole, item.minimumRole));

  return (
    <section className="panel card-stack">
      <h2 className="section-title">{t("control.title", { username: displayName })}</h2>
      <p className="status-text">{t("control.description")}</p>
      <OptionCardGrid items={visibleItems} ariaLabel={t("control.aria")} />
    </section>
  );
}
