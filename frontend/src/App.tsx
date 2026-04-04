import { Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthProvider";
import { RequireAuth, RequireRole } from "./auth/RouteGuards";
import { getDefaultRouteForRole } from "./auth/roles";
import AppChrome from "./features/app-shell/AppChrome";
import NotFoundPage from "./pages/NotFoundPage";
import { appRoutes, type AppRouteDefinition } from "./routes/appRoutes";

function AuthRedirect({ children }: { children: JSX.Element }): JSX.Element {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <p className="status-text">Loading...</p>;
  }

  if (isAuthenticated && user) {
    return <Navigate to={getDefaultRouteForRole(user.role)} replace />;
  }

  return children;
}

function renderRouteElement(route: AppRouteDefinition): JSX.Element {
  const routeElement = (
    <Suspense fallback={<p className="status-text">Loading...</p>}>
      {route.element}
    </Suspense>
  );

  if (route.guestOnly) {
    return <AuthRedirect>{routeElement}</AuthRedirect>;
  }

  if (route.minimumRole) {
    return <RequireRole role={route.minimumRole}>{routeElement}</RequireRole>;
  }

  if (route.requiresAuth) {
    return <RequireAuth>{routeElement}</RequireAuth>;
  }

  return routeElement;
}

export default function App(): JSX.Element {
  return (
    <AppChrome>
      <Routes>
        {appRoutes.map((route) => (
          <Route key={route.id} path={route.path} element={renderRouteElement(route)} />
        ))}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AppChrome>
  );
}
