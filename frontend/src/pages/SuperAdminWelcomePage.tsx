import { Link } from "react-router-dom";
import { hasRequiredRole } from "../auth/roles";
import type { Role } from "../auth/types";

type AvailableItem = {
  title: string;
  description: string;
  to: string;
  minimumRole: Role;
};

const availableItems: AvailableItem[] = [
  {
    title: "View your profile",
    description: "Confirm identity, account status, and role information.",
    to: "/settings",
    minimumRole: "user",
  },
  {
    title: "Process user approvals",
    description: "Use admin approval workflow to activate pending accounts.",
    to: "/admin/approvals",
    minimumRole: "admin",
  },
  {
    title: "Open user welcome page",
    description: "Review the basic onboarding options for normal users.",
    to: "/welcome/user",
    minimumRole: "user",
  },
  {
    title: "Open admin welcome page",
    description: "Review administrator-level landing actions and navigation.",
    to: "/welcome/admin",
    minimumRole: "admin",
  },
  {
    title: "Open superadmin welcome page",
    description: "Return to this page to access full role-level capability overview.",
    to: "/welcome/superadmin",
    minimumRole: "superadmin",
  },
];

export default function SuperAdminWelcomePage(): JSX.Element {
  const visibleItems = availableItems.filter((item) => hasRequiredRole("superadmin", item.minimumRole));

  return (
    <section className="panel card-stack">
      <h2 className="section-title">Welcome, Superadmin</h2>
      <p className="status-text">Here are all currently available items for superadmin users.</p>
      <ul className="card-stack" aria-label="Superadmin available items">
        {visibleItems.map((item) => (
          <li key={item.to}>
            <strong>{item.title}</strong>
            <p className="status-text">{item.description}</p>
            <Link className="link-chip" to={item.to}>{item.to}</Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
