import { useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth/AuthProvider";
import { RequireAuth, RequireRole } from "./auth/RouteGuards";
import { getDefaultRouteForRole } from "./auth/roles";
import { useRuntimeMode } from "./runtime/RuntimeModeProvider";
import NotFoundPage from "./pages/NotFoundPage";
import { appRoutes, getBreadcrumbRoutes, getNavRoutes, type AppRouteDefinition } from "./routes/appRoutes";

type RuntimeModeConfirmationDialogProps = {
  nextMode: "air_gapped" | "online";
  isPending: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

function RuntimeModeConfirmationDialog({
  nextMode,
  isPending,
  onCancel,
  onConfirm,
}: RuntimeModeConfirmationDialogProps): JSX.Element {
  const { t } = useTranslation("common");
  const confirmButtonRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    confirmButtonRef.current?.focus();
  }, []);

  useEffect(() => {
    const handleEscapePress = (event: KeyboardEvent): void => {
      if (event.key === "Escape" && !isPending) {
        onCancel();
      }
    };

    document.addEventListener("keydown", handleEscapePress);
    return () => {
      document.removeEventListener("keydown", handleEscapePress);
    };
  }, [isPending, onCancel]);

  const titleKey = nextMode === "air_gapped"
    ? "runtimeMode.dialog.titleLocalOnly"
    : "runtimeMode.dialog.titleOnline";
  const messageKey = nextMode === "air_gapped"
    ? "runtimeMode.confirmEnableLocalOnly"
    : "runtimeMode.confirmEnableOnline";
  const confirmLabelKey = nextMode === "air_gapped"
    ? "runtimeMode.dialog.confirmLocalOnly"
    : "runtimeMode.dialog.confirmOnline";

  return (
    <div className="modal-backdrop" role="presentation">
      <div
        className="modal-card panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="runtime-mode-dialog-title"
        aria-describedby="runtime-mode-dialog-message"
      >
        <p className="eyebrow">{t("runtimeMode.toggleLabel")}</p>
        <h2 id="runtime-mode-dialog-title" className="section-title modal-title">
          {t(titleKey)}
        </h2>
        <p id="runtime-mode-dialog-message" className="modal-message">
          {t(messageKey)}
        </p>
        <div className="modal-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={onCancel}
            disabled={isPending}
          >
            {t("runtimeMode.dialog.cancel")}
          </button>
          <button
            ref={confirmButtonRef}
            type="button"
            className="primary-button"
            onClick={onConfirm}
            disabled={isPending}
          >
            {t(confirmLabelKey)}
          </button>
        </div>
      </div>
    </div>
  );
}

function AppHeader(): JSX.Element {
  const { t } = useTranslation("common");
  const { user, isAuthenticated, logout } = useAuth();
  const { mode, isLoading: isRuntimeLoading, isSaving: isRuntimeSaving, error: runtimeError, setMode } = useRuntimeMode();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [pendingRuntimeMode, setPendingRuntimeMode] = useState<"air_gapped" | "online" | null>(null);
  const menuContainerRef = useRef<HTMLDivElement | null>(null);
  const menuId = useId();

  const displayName = isAuthenticated ? user?.username ?? user?.email ?? t("nav.guest") : t("nav.guest");
  const runtimeModeLabel = mode ? t(`runtimeMode.${mode === "air_gapped" ? "airGapped" : mode}`) : "--";
  const canUpdateRuntimeMode = user?.role === "superadmin";
  const isRuntimeToggleDisabled = !canUpdateRuntimeMode || isRuntimeLoading || isRuntimeSaving || !mode;
  const isLocalOnlyMode = mode ? mode !== "online" : false;
  const primaryNavRoutes = getNavRoutes("primary", { isAuthenticated });
  const userMenuRoutes = getNavRoutes("userMenu", { isAuthenticated });

  const handleRuntimeModeRequest = (nextMode: "air_gapped" | "online"): void => {
    setPendingRuntimeMode(nextMode);
  };

  const handleRuntimeModeCancel = (): void => {
    setPendingRuntimeMode(null);
  };

  const handleRuntimeModeConfirm = (): void => {
    if (!pendingRuntimeMode) {
      return;
    }

    const nextMode = pendingRuntimeMode;
    setPendingRuntimeMode(null);
    void setMode(nextMode);
  };

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
          {primaryNavRoutes.map((route) => (
            <Link key={route.id} to={route.path} className="link-chip">
              {t(route.titleKey)}
            </Link>
          ))}
        </nav>
        <div className="nav-links user-menu" role="group" aria-label={t("nav.settingsMenuLabel")} ref={menuContainerRef}>
          <label className="runtime-toggle" title={canUpdateRuntimeMode ? t("runtimeMode.toggleTooltip", { mode: runtimeModeLabel }) : t("runtimeMode.permissionDenied")}>
            <span className="runtime-toggle-text">{t("runtimeMode.localOnlyLabel")}</span>
            <input
              type="checkbox"
              role="switch"
              aria-label={t("runtimeMode.toggleLabel")}
              disabled={isRuntimeToggleDisabled}
              checked={isLocalOnlyMode}
              onChange={(event) => {
                if (!mode || isRuntimeToggleDisabled) {
                  return;
                }

                const nextMode = event.currentTarget.checked ? "air_gapped" : "online";
                handleRuntimeModeRequest(nextMode);
              }}
            />
            <span className="runtime-toggle-track" aria-hidden="true">
              <span className="runtime-toggle-thumb" />
            </span>
          </label>
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
              {userMenuRoutes.map((route) => (
                <Link
                  key={route.id}
                  to={route.path}
                  className="user-menu-item"
                  onClick={() => setIsMenuOpen(false)}
                >
                  {t(route.titleKey)}
                </Link>
              ))}
              {isAuthenticated && (
                <>
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
        {runtimeError && <p className="status-text">{runtimeError === "runtimeMode.updateFailed" ? t("runtimeMode.updateFailed") : runtimeError}</p>}
      </div>
      {pendingRuntimeMode && (
        <RuntimeModeConfirmationDialog
          nextMode={pendingRuntimeMode}
          isPending={isRuntimeSaving}
          onCancel={handleRuntimeModeCancel}
          onConfirm={handleRuntimeModeConfirm}
        />
      )}
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

function BreadcrumbsBar(): JSX.Element {
  const { t } = useTranslation("common");
  const location = useLocation();
  const matchedRoutes = getBreadcrumbRoutes(location.pathname);
  const homeRoute = appRoutes.find((route) => route.path === "/");
  const nonHomeRoutes = matchedRoutes.filter((route) => route.path !== "/");
  const crumbs = homeRoute ? [homeRoute, ...nonHomeRoutes] : nonHomeRoutes;

  return (
    <nav className="breadcrumb-bar panel" aria-label={t("nav.breadcrumbs.aria")}>
      <ol className="breadcrumb-list">
        {crumbs.map((crumb, index) => (
          <li key={crumb.path} className="breadcrumb-item">
            {index === crumbs.length - 1 ? (
              <span className="breadcrumb-current" aria-current="page">{t(crumb.titleKey)}</span>
            ) : (
              <Link to={crumb.path} className="breadcrumb-link">{t(crumb.titleKey)}</Link>
            )}
            {index < crumbs.length - 1 && <span className="breadcrumb-separator" aria-hidden="true">/</span>}
          </li>
        ))}
      </ol>
    </nav>
  );
}

function renderRouteElement(route: AppRouteDefinition): JSX.Element {
  if (route.guestOnly) {
    return <AuthRedirect>{route.element}</AuthRedirect>;
  }

  if (route.minimumRole) {
    return <RequireRole role={route.minimumRole}>{route.element}</RequireRole>;
  }

  if (route.requiresAuth) {
    return <RequireAuth>{route.element}</RequireAuth>;
  }

  return route.element;
}

export default function App(): JSX.Element {
  return (
    <main className="page-shell">
      <AppHeader />
      <BreadcrumbsBar />
      <Routes>
        {appRoutes.map((route) => (
          <Route key={route.id} path={route.path} element={renderRouteElement(route)} />
        ))}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </main>
  );
}
