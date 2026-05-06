import { useEffect, useId, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router-dom";
import { useAuth } from "../../auth/AuthProvider";
import AppSidebar from "../../components/AppSidebar";
import AppTopBar from "../../components/AppTopBar";
import { useActionFeedback } from "../../feedback/ActionFeedbackProvider";
import { useRuntimeMode } from "../../runtime/RuntimeModeProvider";
import { getMainContentLayout } from "../../routes/appRoutes";
import { buildSidebarItems, buildTopBarPathItems, buildUserMenuItems } from "./navigation";
import { useAppShellState } from "./useAppShellState";

const VANESSA_DOCS_URL = "https://raul-arrabales.github.io/VANESSA/";

type RuntimeModeConfirmationDialogProps = {
  nextMode: "offline" | "online";
  isPending: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

type RuntimeModeIconProps = {
  mode: "offline" | "online" | null;
};

function RuntimeModeIcon({ mode }: RuntimeModeIconProps): JSX.Element {
  if (mode === "online") {
    return (
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M7.5 18.5a5 5 0 0 1-.66-9.95 6.25 6.25 0 0 1 11.75 2.12A4 4 0 0 1 18 18.5H7.5Zm0-2h10.44a2 2 0 0 0 .18-4h-1.35l-.16-1.34a4.25 4.25 0 0 0-8.18-1.11l-.39.97-1.04.03a3 3 0 0 0 .08 6h.42v1.45Z" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path d="m4.1 3 16.9 16.9-1.4 1.4-2.83-2.83H7.5a5 5 0 0 1-.66-9.95A6.22 6.22 0 0 1 7.88 6.2L2.7 4.4 4.1 3Zm3.4 13.5h7.27L9.35 11.08l-.92-1.03-.39.97-1.04.03a3 3 0 0 0 .08 6h.42v-.55Zm1.82-11.14a6.25 6.25 0 0 1 9.27 5.31A4 4 0 0 1 18 18.5h-.06l-1.99-2h1.99a2 2 0 0 0 .18-4h-1.35l-.16-1.34a4.24 4.24 0 0 0-5.8-3.35L9.32 5.36Z" />
    </svg>
  );
}

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
  const nextRuntimeMode = isOfflineMode ? "online" : "offline";
  const nextRuntimeModeLabel = t(`runtimeMode.${nextRuntimeMode}`);
  const userMenuRoutes = buildUserMenuItems(isAuthenticated, t);
  const sidebarItems = buildSidebarItems(location.pathname, {
    isAuthenticated,
    role: user?.role ?? null,
  }, t);
  const pathItems = buildTopBarPathItems(location.pathname, t);
  const mainContentLayout = getMainContentLayout(location.pathname);

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
      <button
        type="button"
        className="runtime-mode-pill"
        data-mode={mode ?? "unknown"}
        aria-label={t("runtimeMode.toggleLabel")}
        disabled={isRuntimeToggleDisabled}
        title={
          !canUpdateRuntimeMode
            ? t("runtimeMode.permissionDenied")
            : isRuntimeLocked
              ? t("runtimeMode.lockedByEnvironment", { mode: runtimeModeLabel })
              : t("runtimeMode.switchTooltip", { mode: runtimeModeLabel, nextMode: nextRuntimeModeLabel })
        }
        onClick={() => {
          if (!mode || isRuntimeToggleDisabled) {
            return;
          }

          requestRuntimeMode(nextRuntimeMode);
        }}
      >
        <span className="runtime-mode-icon">
          <RuntimeModeIcon mode={mode} />
        </span>
        {mode === "online" ? (
          <span className="runtime-transfer-indicators" aria-hidden="true">
            <span className="runtime-transfer-indicator" data-direction="upload" data-active="false">
              <svg viewBox="0 0 12 12" focusable="false">
                <path d="M6 2 2.8 5.2l.9.9L5.35 4.45V10h1.3V4.45L8.3 6.1l.9-.9L6 2Z" />
              </svg>
            </span>
            <span className="runtime-transfer-indicator" data-direction="download" data-active="false">
              <svg viewBox="0 0 12 12" focusable="false">
                <path d="M5.35 2v5.55L3.7 5.9l-.9.9L6 10l3.2-3.2-.9-.9-1.65 1.65V2h-1.3Z" />
              </svg>
            </span>
          </span>
        ) : null}
      </button>
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
          docsLabel={t("nav.docs")}
          docsUrl={VANESSA_DOCS_URL}
          onToggleNavigationDrawer={toggleSidebarDrawer}
          onToggleUserMenu={toggleUserMenu}
          onCloseUserMenu={closeUserMenu}
          onLogout={() => {
            closeUserMenu();
            void logout();
          }}
          logoutLabel={t("auth.logout")}
        />
        <main className="app-main-content" data-layout={mainContentLayout}>
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
