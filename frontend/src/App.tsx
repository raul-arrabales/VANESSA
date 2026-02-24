import { useTranslation } from "react-i18next";
import { Link, Navigate, Route, Routes } from "react-router-dom";
import LanguageSwitcher from "./components/LanguageSwitcher";
import ThemeToggle from "./components/ThemeToggle";
import { useAuth } from "./auth/AuthProvider";
import { RequireAuth, RequireRole } from "./auth/RouteGuards";
import { getDefaultRouteForRole } from "./auth/roles";
import AdminApprovalsPage from "./pages/AdminApprovalsPage";
import AdminWelcomePage from "./pages/AdminWelcomePage";
import HomePage from "./pages/HomePage";
import BackendHealthPage from "./pages/BackendHealthPage";
import LoginPage from "./pages/LoginPage";
import ProfilePage from "./pages/ProfilePage";
import RegisterPage from "./pages/RegisterPage";
import StyleGuidePage from "./pages/StyleGuidePage";
import SuperAdminWelcomePage from "./pages/SuperAdminWelcomePage";
import UserWelcomePage from "./pages/UserWelcomePage";

function AppHeader(): JSX.Element {
  const { t } = useTranslation("common");
  const { user, isAuthenticated, logout } = useAuth();

  const canAccessApprovals = user?.role === "admin" || user?.role === "superadmin";
  const welcomeLabelKey = user?.role ? `nav.welcome.${user.role}` : "nav.welcome.user";
  const welcomeRoute = user?.role ? getDefaultRouteForRole(user.role) : "/welcome/user";

  return (
    <header className="app-header panel">
      <div>
        <p className="eyebrow">{t("app.eyebrow")}</p>
        <h1 className="app-title">{t("app.title")}</h1>
        <p className="subtitle">{t("app.subtitle")}</p>
      </div>
      <div className="toolbar" role="group" aria-label={t("app.controls") }>
        <nav className="nav-links" aria-label={t("nav.aria")}>
          <Link to="/" className="link-chip">{t("nav.home")}</Link>
          <Link to="/style-guide" className="link-chip">{t("nav.styleGuide")}</Link>
          <Link to="/backend-health" className="link-chip">{t("nav.backendHealth")}</Link>
          {!isAuthenticated && <Link to="/login" className="link-chip">{t("nav.login")}</Link>}
          {!isAuthenticated && <Link to="/register" className="link-chip">{t("nav.register")}</Link>}
          {isAuthenticated && <Link to={welcomeRoute} className="link-chip">{t(welcomeLabelKey)}</Link>}
          {isAuthenticated && <Link to="/me" className="link-chip">{t("nav.me")}</Link>}
          {isAuthenticated && canAccessApprovals && (
            <Link to="/admin/approvals" className="link-chip">{t("nav.approvals")}</Link>
          )}
          {isAuthenticated && (
            <button type="button" className="btn btn-ghost nav-logout" onClick={() => void logout()}>
              {t("auth.logout")}
            </button>
          )}
        </nav>
        <ThemeToggle />
        <LanguageSwitcher />
      </div>
    </header>
  );
}

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

export default function App(): JSX.Element {
  return (
    <main className="page-shell">
      <AppHeader />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/style-guide" element={<StyleGuidePage />} />
        <Route path="/backend-health" element={<BackendHealthPage />} />
        <Route
          path="/login"
          element={(
            <AuthRedirect>
              <LoginPage />
            </AuthRedirect>
          )}
        />
        <Route
          path="/register"
          element={(
            <AuthRedirect>
              <RegisterPage />
            </AuthRedirect>
          )}
        />
        <Route
          path="/welcome/user"
          element={(
            <RequireRole role="user">
              <UserWelcomePage />
            </RequireRole>
          )}
        />
        <Route
          path="/welcome/admin"
          element={(
            <RequireRole role="admin">
              <AdminWelcomePage />
            </RequireRole>
          )}
        />
        <Route
          path="/welcome/superadmin"
          element={(
            <RequireRole role="superadmin">
              <SuperAdminWelcomePage />
            </RequireRole>
          )}
        />
        <Route
          path="/me"
          element={(
            <RequireAuth>
              <ProfilePage />
            </RequireAuth>
          )}
        />
        <Route
          path="/admin/approvals"
          element={(
            <RequireRole role="admin">
              <AdminApprovalsPage />
            </RequireRole>
          )}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </main>
  );
}
