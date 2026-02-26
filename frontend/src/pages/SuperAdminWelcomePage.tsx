import { useAuth } from "../auth/AuthProvider";
import { hasRequiredRole } from "../auth/roles";
import type { Role } from "../auth/types";
import OptionCardGrid, { type OptionCardIconName } from "../components/OptionCardGrid";
import { useTranslation } from "react-i18next";

type AvailableItem = {
  id: string;
  title: string;
  description: string;
  to: string;
  icon: OptionCardIconName;
  minimumRole: Role;
};

export default function SuperAdminWelcomePage(): JSX.Element {
  const { t } = useTranslation("common");
  const { user } = useAuth();
  const availableItems: AvailableItem[] = [
    {
      id: "profile",
      title: "View your profile",
      description: "Confirm identity, account status, and role information.",
      to: "/settings",
      icon: "profile",
      minimumRole: "user",
    },
    {
      id: "approvals",
      title: "Process user approvals",
      description: "Use admin approval workflow to activate pending accounts.",
      to: "/admin/approvals",
      icon: "approvals",
      minimumRole: "admin",
    },
    {
      id: "backend-health",
      title: "Backend health",
      description: "Run backend diagnostics and verify API connectivity from the UI.",
      to: "/backend-health",
      icon: "health",
      minimumRole: "superadmin",
    },
    {
      id: "models",
      title: t("models.title"),
      description: t("models.subtitle"),
      to: "/welcome/superadmin/models",
      icon: "models",
      minimumRole: "superadmin",
    },
    {
      id: "user-welcome",
      title: "Open user welcome page",
      description: "Review the basic onboarding options for normal users.",
      to: "/welcome/user",
      icon: "userPage",
      minimumRole: "user",
    },
    {
      id: "admin-welcome",
      title: "Open admin welcome page",
      description: "Review administrator-level landing actions and navigation.",
      to: "/welcome/admin",
      icon: "adminPage",
      minimumRole: "admin",
    },
  ];
  const visibleItems = availableItems.filter((item) => hasRequiredRole("superadmin", item.minimumRole));
  const superadminName = user?.username ?? user?.email ?? "Superadmin";

  return (
    <section className="panel card-stack">
      <h2 className="section-title">Welcome to the superadmin control panel, {superadminName}</h2>
      <p className="status-text">Here are all currently available items for superadmin users.</p>
      <OptionCardGrid items={visibleItems} ariaLabel="Superadmin available items" />
    </section>
  );
}
