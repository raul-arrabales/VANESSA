import { Link } from "react-router-dom";
import type { ShellNavItem } from "../features/app-shell/types";
import AppNavIcon from "./AppNavIcon";

type AppSidebarProps = {
  items: ShellNavItem[];
  collapsed: boolean;
  drawerOpen: boolean;
  navLabel: string;
  collapseLabel: string;
  expandLabel: string;
  closeDrawerLabel: string;
  onToggleCollapse: () => void;
  onCloseDrawer: () => void;
};

export default function AppSidebar({
  items,
  collapsed,
  drawerOpen,
  navLabel,
  collapseLabel,
  expandLabel,
  closeDrawerLabel,
  onToggleCollapse,
  onCloseDrawer,
}: AppSidebarProps): JSX.Element {
  return (
    <>
      <button
        type="button"
        className="app-sidebar-backdrop"
        data-open={drawerOpen ? "true" : "false"}
        aria-label={closeDrawerLabel}
        onClick={onCloseDrawer}
      />
      <aside
        className="app-sidebar panel"
        data-testid="app-sidebar"
        data-collapsed={collapsed ? "true" : "false"}
        data-drawer-open={drawerOpen ? "true" : "false"}
      >
        <div className="app-sidebar-header">
          <button
            type="button"
            className="app-sidebar-toggle"
            aria-label={collapsed ? expandLabel : collapseLabel}
            onClick={onToggleCollapse}
          >
            <span className="app-sidebar-toggle-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" focusable="false">
                <path d="M15.5 5.5 9 12l6.5 6.5-1.5 1.5L6 12l8-8 1.5 1.5Z" />
              </svg>
            </span>
            <span className="app-sidebar-toggle-label">{collapsed ? expandLabel : collapseLabel}</span>
          </button>
        </div>
        <nav className="app-sidebar-nav" aria-label={navLabel}>
          <ul className="app-sidebar-list">
            {items.map((item) => (
              <li key={item.id}>
                <Link
                  className="app-sidebar-link"
                  data-active={item.isActive ? "true" : "false"}
                  to={item.to}
                  aria-current={item.isActive ? "page" : undefined}
                  aria-label={collapsed ? item.label : undefined}
                  title={collapsed ? item.label : undefined}
                  onClick={onCloseDrawer}
                >
                  <span className="app-sidebar-link-icon" aria-hidden="true">
                    <AppNavIcon name={item.icon} />
                  </span>
                  <span className="app-sidebar-link-label">{item.label}</span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </aside>
    </>
  );
}
