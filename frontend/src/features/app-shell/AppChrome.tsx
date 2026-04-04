import { useEffect, useId, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router-dom";
import { useAuth } from "../../auth/AuthProvider";
import AppSidebar from "../../components/AppSidebar";
import AppTopBar from "../../components/AppTopBar";
import { useActionFeedback } from "../../feedback/ActionFeedbackProvider";
import { useRuntimeMode } from "../../runtime/RuntimeModeProvider";
import { buildSidebarItems, buildTopBarPathItems, buildUserMenuItems } from "./navigation";
import { useAppShellState } from "./useAppShellState";

type RuntimeModeConfirmationDialogProps = {
  nextMode: "offline" | "online";
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

  const titleKey = nextMode === "offline"
    ? "runtimeMode.dialog.titleOffline"
    : "runtimeMode.dialog.titleOnline";
  const messageKey = nextMode === "offline"
    ? "runtimeMode.confirmEnableOffline"
    : "runtimeMode.confirmEnableOnline";
  const confirmLabelKey = nextMode === "offline"
    ? "runtimeMode.dialog.confirmOffline"
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

export default function AppChrome({ children }: { children: JSX.Element }): JSX.Element {
  const { t } = useTranslation("common");
  const location = useLocation();
  const { user, isAuthenticated, logout } = useAuth();
  const { showErrorFeedback, showSuccessFeedback } = useActionFeedback();
  const {
    mode,
    isLocked: isRuntimeLocked,
    isLoading: isRuntimeLoading,
    isSaving: isRuntimeSaving,
    error: runtimeError,
    setMode,
  } = useRuntimeMode();
  const {
    isMenuOpen,
    isSidebarDrawerOpen,
    isSidebarCollapsed,
    pendingRuntimeMode,
    closeUserMenu,
    toggleUserMenu,
    closeSidebarDrawer,
    toggleSidebarDrawer,
    toggleSidebarCollapsed,
    requestRuntimeMode,
    cancelRuntimeMode,
    clearPendingRuntimeMode,
  } = useAppShellState(location.pathname);
  const menuContainerRef = useRef<HTMLDivElement>(null);
  const handledRuntimeLoadErrorRef = useRef<string>("");
  const menuId = useId();

  const displayName = isAuthenticated ? user?.username ?? user?.email ?? t("nav.guest") : t("nav.guest");
  const runtimeModeLabel = mode ? t(`runtimeMode.${mode}`) : "--";
  const canUpdateRuntimeMode = user?.role === "superadmin";
  const isRuntimeToggleDisabled = !canUpdateRuntimeMode || isRuntimeLocked || isRuntimeLoading || isRuntimeSaving || !mode;
  const isOfflineMode = mode === "offline";
  const userMenuRoutes = buildUserMenuItems(isAuthenticated, t);
  const sidebarItems = buildSidebarItems(location.pathname, {
    isAuthenticated,
    role: user?.role ?? null,
  }, t);
  const pathItems = buildTopBarPathItems(location.pathname, t);

  useEffect(() => {
    if (!runtimeError || !isAuthenticated) {
      handledRuntimeLoadErrorRef.current = "";
      return;
    }

    const message = runtimeError === "settings.runtime.error.load"
      ? t("settings.runtime.error.load")
      : runtimeError;
    if (handledRuntimeLoadErrorRef.current === message) {
      return;
    }

    handledRuntimeLoadErrorRef.current = message;
    showErrorFeedback(message, t("settings.runtime.error.load"));
  }, [isAuthenticated, runtimeError, showErrorFeedback, t]);

  useEffect(() => {
    const handleDocumentClick = (event: MouseEvent): void => {
      if (!menuContainerRef.current?.contains(event.target as Node)) {
        closeUserMenu();
      }
    };

    const handleEscapePress = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        closeUserMenu();
      }
    };

    document.addEventListener("mousedown", handleDocumentClick);
    document.addEventListener("keydown", handleEscapePress);

    return () => {
      document.removeEventListener("mousedown", handleDocumentClick);
      document.removeEventListener("keydown", handleEscapePress);
    };
  }, [closeUserMenu]);

  const handleRuntimeModeConfirm = (): void => {
    if (!pendingRuntimeMode) {
      return;
    }

    const nextMode = pendingRuntimeMode;
    clearPendingRuntimeMode();
    void Promise.resolve(setMode(nextMode))
      .then((updatedMode) => {
        const resolvedMode = updatedMode ?? nextMode;
        showSuccessFeedback(t("runtimeMode.updated", { mode: t(`runtimeMode.${resolvedMode}`) }));
      })
      .catch((saveError: unknown) => {
        showErrorFeedback(saveError, t("runtimeMode.updateFailed"));
      });
  };

  const runtimeControl = (
    <div className="app-topbar-runtime">
      <label
        className="runtime-toggle"
        title={
          !canUpdateRuntimeMode
            ? t("runtimeMode.permissionDenied")
            : isRuntimeLocked
              ? t("runtimeMode.lockedByEnvironment", { mode: runtimeModeLabel })
              : t("runtimeMode.toggleTooltip", { mode: runtimeModeLabel })
        }
      >
        <span className="runtime-toggle-text">{t("runtimeMode.offlineLabel")}</span>
        <input
          type="checkbox"
          role="switch"
          aria-label={t("runtimeMode.toggleLabel")}
          disabled={isRuntimeToggleDisabled}
          checked={isOfflineMode}
          onChange={(event) => {
            if (!mode || isRuntimeToggleDisabled) {
              return;
            }

            requestRuntimeMode(event.currentTarget.checked ? "offline" : "online");
          }}
        />
        <span className="runtime-toggle-track" aria-hidden="true">
          <span className="runtime-toggle-thumb" />
        </span>
      </label>
      {isRuntimeLocked ? (
        <span className="status-text app-topbar-runtime-note">
          {t("runtimeMode.lockedByEnvironment", { mode: runtimeModeLabel })}
        </span>
      ) : null}
    </div>
  );

  return (
    <div className="app-shell" data-sidebar-collapsed={isSidebarCollapsed ? "true" : "false"}>
      <AppSidebar
        items={sidebarItems}
        collapsed={isSidebarCollapsed}
        drawerOpen={isSidebarDrawerOpen}
        navLabel={t("nav.sidebar.aria")}
        collapseLabel={t("nav.sidebar.collapse")}
        expandLabel={t("nav.sidebar.expand")}
        closeDrawerLabel={t("nav.sidebar.close")}
        onToggleCollapse={toggleSidebarCollapsed}
        onCloseDrawer={closeSidebarDrawer}
      />
      <div className="app-main">
        <AppTopBar
          title={t("app.title")}
          controlsLabel={t("app.controls")}
          pathLabel={t("nav.pathCue.aria")}
          openNavigationLabel={t("nav.sidebar.open")}
          displayName={displayName}
          settingsMenuLabel={t("nav.settingsMenuLabel")}
          userMenuRoutes={userMenuRoutes}
          isMenuOpen={isMenuOpen}
          menuId={menuId}
          menuContainerRef={menuContainerRef}
          pathItems={pathItems}
          runtimeControl={runtimeControl}
          showLogout={isAuthenticated}
          onToggleNavigationDrawer={toggleSidebarDrawer}
          onToggleUserMenu={toggleUserMenu}
          onCloseUserMenu={closeUserMenu}
          onLogout={() => {
            closeUserMenu();
            void logout();
          }}
          logoutLabel={t("auth.logout")}
        />
        <main className="app-main-content">
          {children}
        </main>
      </div>
      {pendingRuntimeMode ? (
        <RuntimeModeConfirmationDialog
          nextMode={pendingRuntimeMode}
          isPending={isRuntimeSaving}
          onCancel={cancelRuntimeMode}
          onConfirm={handleRuntimeModeConfirm}
        />
      ) : null}
    </div>
  );
}
