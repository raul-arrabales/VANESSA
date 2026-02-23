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
    title: "Review account profile",
    description: "Inspect your own account metadata and role assignment.",
    to: "/me",
    minimumRole: "user",
  },
  {
    title: "Approve pending users",
    description: "Activate user accounts that are waiting for administrator approval.",
    to: "/admin/approvals",
    minimumRole: "admin",
  },
  {
    title: "Open user welcome page",
    description: "Check what baseline capabilities are visible to standard users.",
    to: "/welcome/user",
    minimumRole: "user",
  },
  {
    title: "Open superadmin welcome page",
    description: "Navigate to elevated controls reserved for superadmin role holders.",
    to: "/welcome/superadmin",
    minimumRole: "superadmin",
  },
];

export default function AdminWelcomePage(): JSX.Element {
  const visibleItems = availableItems.filter((item) => hasRequiredRole("admin", item.minimumRole));

  return (
    <section className="panel card-stack">
      <h2 className="section-title">Welcome, Admin</h2>
      <p className="status-text">Here are the actions available for administrator-level access.</p>
      <ul className="card-stack" aria-label="Admin available items">
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
