import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";
import { hasRequiredRole } from "../auth/roles";
import type { Role } from "../auth/types";

type AvailableItem = {
  title: string;
  description: string;
  actionLabel: string;
  to: string;
  minimumRole: Role;
};

const availableItems: AvailableItem[] = [
  {
    title: "View your profile",
    description: "Confirm identity, account status, and role information.",
    actionLabel: "Open profile",
    to: "/settings",
    minimumRole: "user",
  },
  {
    title: "Process user approvals",
    description: "Use admin approval workflow to activate pending accounts.",
    actionLabel: "Open approvals",
    to: "/admin/approvals",
    minimumRole: "admin",
  },
  {
    title: "Backend health",
    description: "Run backend diagnostics and verify API connectivity from the UI.",
    actionLabel: "Open backend health",
    to: "/backend-health",
    minimumRole: "superadmin",
  },
  {
    title: "Open user welcome page",
    description: "Review the basic onboarding options for normal users.",
    actionLabel: "Open user page",
    to: "/welcome/user",
    minimumRole: "user",
  },
  {
    title: "Open admin welcome page",
    description: "Review administrator-level landing actions and navigation.",
    actionLabel: "Open admin page",
    to: "/welcome/admin",
    minimumRole: "admin",
  },
];

export default function SuperAdminWelcomePage(): JSX.Element {
  const { user } = useAuth();
  const visibleItems = availableItems.filter((item) => hasRequiredRole("superadmin", item.minimumRole));
  const superadminName = user?.username ?? user?.email ?? "Superadmin";

  return (
    <section className="panel card-stack">
      <h2 className="section-title">Welcome to the superadmin control panel, {superadminName}</h2>
      <p className="status-text">Here are all currently available items for superadmin users.</p>
      <ul className="welcome-tile-grid" aria-label="Superadmin available items">
        {visibleItems.map((item) => (
          <li key={item.to} className="welcome-tile panel">
            <h3 className="section-title">{item.title}</h3>
            <p className="status-text">{item.description}</p>
            <Link className="btn btn-primary" to={item.to}>{item.actionLabel}</Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
