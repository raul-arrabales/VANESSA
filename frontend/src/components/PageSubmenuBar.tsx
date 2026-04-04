import { Link } from "react-router-dom";
import type { PageSubmenuItem } from "./navigation";

type PageSubmenuBarProps = {
  items: PageSubmenuItem[];
  ariaLabel: string;
};

export default function PageSubmenuBar({ items, ariaLabel }: PageSubmenuBarProps): JSX.Element {
  return (
    <nav className="page-submenu-bar" aria-label={ariaLabel}>
      {items.map((item) => (
        item.to ? (
          <Link
            key={item.id}
            className="page-submenu-item"
            data-active={item.isActive ? "true" : "false"}
            to={item.to}
            aria-current={item.isActive ? "page" : undefined}
          >
            {item.label}
          </Link>
        ) : (
          <button
            key={item.id}
            type="button"
            className="page-submenu-item"
            data-active={item.isActive ? "true" : "false"}
            aria-pressed={item.isActive}
            onClick={item.onSelect}
          >
            {item.label}
          </button>
        )
      ))}
    </nav>
  );
}
