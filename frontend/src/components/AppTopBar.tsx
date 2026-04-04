import type { RefObject } from "react";
import { Link } from "react-router-dom";
import type { TopBarPathItem, UserMenuItem } from "../features/app-shell/types";
import VanessaBrand from "./VanessaBrand";

type AppTopBarProps = {
  title: string;
  controlsLabel: string;
  pathLabel: string;
  openNavigationLabel: string;
  displayName: string;
  settingsMenuLabel: string;
  userMenuRoutes: UserMenuItem[];
  isMenuOpen: boolean;
  menuId: string;
  menuContainerRef: RefObject<HTMLDivElement>;
  pathItems: TopBarPathItem[];
  runtimeControl: JSX.Element;
  showLogout: boolean;
  onToggleNavigationDrawer: () => void;
  onToggleUserMenu: () => void;
  onCloseUserMenu: () => void;
  onLogout: () => void;
  logoutLabel: string;
};

export default function AppTopBar({
  title,
  controlsLabel,
  pathLabel,
  openNavigationLabel,
  displayName,
  settingsMenuLabel,
  userMenuRoutes,
  isMenuOpen,
  menuId,
  menuContainerRef,
  pathItems,
  runtimeControl,
  showLogout,
  onToggleNavigationDrawer,
  onToggleUserMenu,
  onCloseUserMenu,
  onLogout,
  logoutLabel,
}: AppTopBarProps): JSX.Element {
  return (
    <header className="app-topbar panel">
      <div className="app-topbar-leading">
        <button
          type="button"
          className="app-topbar-menu-button"
          aria-label={openNavigationLabel}
          onClick={onToggleNavigationDrawer}
        >
          <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
            <path d="M4 7h16v2H4V7Zm0 8h16v2H4v-2Zm0-4h16v2H4v-2Z" />
          </svg>
        </button>
        <Link className="app-topbar-brand" to="/">
          <VanessaBrand
            className="app-topbar-brand-mark"
            label={title}
            variant="monogram"
            hoverMode="soft-glow"
          />
        </Link>
      </div>
      <div className="app-topbar-path" aria-label={pathLabel}>
        {pathItems.map((item, index) => (
          <span key={item.id} className="app-topbar-path-segment">
            {index > 0 ? <span className="app-topbar-path-separator" aria-hidden="true">/</span> : null}
            {item.isCurrent ? (
              <span className="app-topbar-path-current">{item.label}</span>
            ) : (
              <Link className="app-topbar-path-link app-topbar-path-text" to={item.to}>
                {item.label}
              </Link>
            )}
          </span>
        ))}
      </div>
      <div className="app-topbar-actions" role="group" aria-label={controlsLabel}>
        {runtimeControl}
        <div className="user-menu" role="group" aria-label={settingsMenuLabel} ref={menuContainerRef}>
          <button
            type="button"
            className="user-menu-trigger"
            aria-expanded={isMenuOpen}
            aria-controls={menuId}
            onClick={onToggleUserMenu}
          >
            <span className="user-menu-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" focusable="false">
                <path d="M12 12.5a4.25 4.25 0 1 0-4.25-4.25A4.25 4.25 0 0 0 12 12.5Z" />
                <path d="M12 13.75c-4.28 0-7.75 2.69-7.75 6v.5h15.5v-.5c0-3.31-3.47-6-7.75-6Z" />
              </svg>
            </span>
            <span className="user-menu-label">{displayName}</span>
          </button>
          {isMenuOpen ? (
            <div id={menuId} className="user-menu-panel">
              {userMenuRoutes.map((route) => (
                <Link key={route.id} to={route.to} className="user-menu-item" onClick={onCloseUserMenu}>
                  {route.label}
                </Link>
              ))}
              {showLogout ? (
                <button type="button" className="user-menu-item user-menu-button" onClick={onLogout}>
                  {logoutLabel}
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}
