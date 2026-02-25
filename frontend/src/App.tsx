import { useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthProvider";
import { RequireAuth, RequireRole } from "./auth/RouteGuards";
import { getDefaultRouteForRole } from "./auth/roles";
import AdminApprovalsPage from "./pages/AdminApprovalsPage";
import AdminWelcomePage from "./pages/AdminWelcomePage";
import HomePage from "./pages/HomePage";
import ChatbotPage from "./pages/ChatbotPage";
import BackendHealthPage from "./pages/BackendHealthPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import SettingsPage from "./pages/SettingsPage";
import StyleGuidePage from "./pages/StyleGuidePage";
import SuperAdminWelcomePage from "./pages/SuperAdminWelcomePage";
import UserWelcomePage from "./pages/UserWelcomePage";

function AppHeader(): JSX.Element {
  const { t } = useTranslation("common");
  const { user, isAuthenticated, logout } = useAuth();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuContainerRef = useRef<HTMLDivElement | null>(null);
  const menuId = useId();

  const canAccessApprovals = user?.role === "admin" || user?.role === "superadmin";
  const welcomeLabelKey = user?.role ? `nav.welcome.${user.role}` : "nav.welcome.user";
  const welcomeRoute = user?.role ? getDefaultRouteForRole(user.role) : "/welcome/user";
  const displayName = isAuthenticated ? user?.username ?? user?.email ?? t("nav.guest") : t("nav.guest");

  useEffect(() => {
    const handleDocumentClick = (event: MouseEvent): void => {
      if (!menuContainerRef.current?.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    };

    const handleEscapePress = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        setIsMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", handleDocumentClick);
    document.addEventListener("keydown", handleEscapePress);

    return () => {
      document.removeEventListener("mousedown", handleDocumentClick);
      document.removeEventListener("keydown", handleEscapePress);
    };
  }, []);

  return (
    <header className="app-header panel">
      <div>
        <p className="eyebrow">{t("app.eyebrow")}</p>
        <h1 className="app-title">{t("app.title")}</h1>
        <p className="subtitle">{t("app.subtitle")}</p>
      </div>
      <div className="toolbar" role="group" aria-label={t("app.controls") }>
        <nav className="nav-links" aria-label={t("nav.aria")}>
          {!isAuthenticated && <Link to="/" className="link-chip">{t("nav.home")}</Link>}
          {isAuthenticated && <Link to="/backend-health" className="link-chip">{t("nav.backendHealth")}</Link>}
          {isAuthenticated && <Link to="/chat" className="link-chip">Chatbot</Link>}
          {isAuthenticated && <Link to={welcomeRoute} className="link-chip">{t(welcomeLabelKey)}</Link>}
          {isAuthenticated && canAccessApprovals && (
            <Link to="/admin/approvals" className="link-chip">{t("nav.approvals")}</Link>
          )}
        </nav>
        <div className="nav-links user-menu" role="group" aria-label={t("nav.settingsMenuLabel")} ref={menuContainerRef}>
          <button
            type="button"
            className="user-menu-trigger"
            aria-expanded={isMenuOpen}
            aria-controls={menuId}
            onClick={() => setIsMenuOpen((currentState) => !currentState)}
          >
            <span className="user-menu-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" focusable="false">
                <path d="M12 12.5a4.25 4.25 0 1 0-4.25-4.25A4.25 4.25 0 0 0 12 12.5Z" />
                <path d="M12 13.75c-4.28 0-7.75 2.69-7.75 6v.5h15.5v-.5c0-3.31-3.47-6-7.75-6Z" />
              </svg>
            </span>
            <span className="user-menu-label">{displayName}</span>
          </button>
          {isMenuOpen && (
            <div id={menuId} className="user-menu-panel">
              {!isAuthenticated && <Link to="/login" className="user-menu-item" onClick={() => setIsMenuOpen(false)}>{t("nav.login")}</Link>}
              {isAuthenticated && (
                <>
                  <Link to="/settings" className="user-menu-item" onClick={() => setIsMenuOpen(false)}>{t("nav.settings")}</Link>
                  <button
                    type="button"
                    className="user-menu-item user-menu-button"
                    onClick={() => {
                      setIsMenuOpen(false);
                      void logout();
                    }}
                  >
                    {t("auth.logout")}
                  </button>
                </>
              )}
            </div>
          )}
        </div>
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
        <Route path="/backend-health" element={<BackendHealthPage />} />
        <Route
          path="/chat"
          element={(
            <RequireAuth>
              <ChatbotPage />
            </RequireAuth>
          )}
        />
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
          path="/settings"
          element={(
            <RequireAuth>
              <SettingsPage />
            </RequireAuth>
          )}
        >
          <Route
            path="design"
            element={(
              <RequireRole role="superadmin">
                <StyleGuidePage />
              </RequireRole>
            )}
          />
        </Route>
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
