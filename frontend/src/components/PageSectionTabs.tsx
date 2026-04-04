import { Link } from "react-router-dom";
import type { PageSectionTabItem } from "./navigation";

type PageSectionTabsProps = {
  items: PageSectionTabItem[];
  ariaLabel: string;
};

export default function PageSectionTabs({ items, ariaLabel }: PageSectionTabsProps): JSX.Element {
  return (
    <nav className="page-section-tabs" aria-label={ariaLabel}>
      {items.map((item) => (
        <Link
          key={item.id}
          className="page-section-tab"
          data-active={item.isActive ? "true" : "false"}
          to={item.to}
          aria-current={item.isActive ? "page" : undefined}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
