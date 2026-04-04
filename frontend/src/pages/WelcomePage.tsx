import { Link, Navigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthProvider";
import { getDefaultRouteForRole } from "../auth/roles";
import type { Role } from "../auth/types";
import VanessaBrand from "../components/VanessaBrand";

type WelcomePageProps = {
  role: Role;
};

export default function WelcomePage({ role }: WelcomePageProps): JSX.Element {
  const { t } = useTranslation("common");
  const { user } = useAuth();

  if (!user) {
    return <p className="status-text">Loading...</p>;
  }

  if (user.role !== role) {
    return <Navigate to={getDefaultRouteForRole(user.role)} replace />;
  }

  return (
    <section className="panel card-stack">
      <div className="app-brand welcome-page-brand">
        <h1 className="app-brand-title">
          <VanessaBrand
            className="app-brand-display welcome-page-brand-display"
            label={t("app.title")}
            hoverMode="soft-glow"
          />
        </h1>
      </div>
      <h2 className="section-title">Welcome, {role}</h2>
      <p className="status-text">You are signed in with {role} access.</p>
      <div className="form-actions">
        <Link to="/settings" className="btn btn-primary">View profile</Link>
        {(role === "admin" || role === "superadmin") && (
          <Link to="/control/approvals" className="btn btn-ghost">Open approvals</Link>
        )}
      </div>
    </section>
  );
}
