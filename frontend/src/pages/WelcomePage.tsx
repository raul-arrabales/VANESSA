import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";
import { getDefaultRouteForRole } from "../auth/roles";
import type { Role } from "../auth/types";

type WelcomePageProps = {
  role: Role;
};

export default function WelcomePage({ role }: WelcomePageProps): JSX.Element {
  const { user } = useAuth();

  if (!user) {
    return <p className="status-text">Loading...</p>;
  }

  if (user.role !== role) {
    return <Navigate to={getDefaultRouteForRole(user.role)} replace />;
  }

  return (
    <section className="panel card-stack">
      <h2 className="section-title">Welcome, {role}</h2>
      <p className="status-text">You are signed in with {role} access.</p>
      <div className="form-actions">
        <Link to="/me" className="btn btn-primary">View profile</Link>
        {(role === "admin" || role === "superadmin") && (
          <Link to="/admin/approvals" className="btn btn-ghost">Open approvals</Link>
        )}
      </div>
    </section>
  );
}
