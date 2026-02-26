import { Navigate, useLocation } from "react-router-dom";
import { hasRequiredRole } from "./roles";
import { useAuth } from "./AuthProvider";
import type { Role } from "./types";

type GuardProps = {
  children: JSX.Element;
};

type RoleGuardProps = GuardProps & {
  role: Role;
};

export function RequireAuth({ children }: GuardProps): JSX.Element {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <p className="status-text">Loading...</p>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return children;
}

export function RequireRole({ role, children }: RoleGuardProps): JSX.Element {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <p className="status-text">Loading...</p>;
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  if (!hasRequiredRole(user.role, role)) {
    return (
      <section className="panel card-stack">
        <h2 className="section-title">Forbidden</h2>
        <p className="status-text">You do not have permission to access this page.</p>
      </section>
    );
  }

  return children;
}
