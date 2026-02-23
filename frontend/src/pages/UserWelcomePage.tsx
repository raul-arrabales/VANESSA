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
    description: "Review your account details, active status, and role membership.",
    to: "/me",
    minimumRole: "user",
  },
  {
    title: "Browse the style guide",
    description: "See the UI patterns used throughout VANESSA's frontend.",
    to: "/style-guide",
    minimumRole: "user",
  },
  {
    title: "Access admin approvals",
    description: "Approve pending users once you have admin-level privileges.",
    to: "/admin/approvals",
    minimumRole: "admin",
  },
  {
    title: "Open the admin welcome area",
    description: "Navigate to the dedicated admin landing page.",
    to: "/welcome/admin",
    minimumRole: "admin",
  },
  {
    title: "Open the superadmin welcome area",
    description: "Navigate to the superadmin control landing page.",
    to: "/welcome/superadmin",
    minimumRole: "superadmin",
  },
];

export default function UserWelcomePage(): JSX.Element {
  const visibleItems = availableItems.filter((item) => hasRequiredRole("user", item.minimumRole));

  return (
    <section className="panel card-stack">
      <h2 className="section-title">Welcome, User</h2>
      <p className="status-text">Here are the actions currently available for the user role.</p>
      <ul className="card-stack" aria-label="User available items">
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
