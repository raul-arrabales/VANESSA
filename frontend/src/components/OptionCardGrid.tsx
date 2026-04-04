import { Link } from "react-router-dom";
import AppNavIcon, { type AppNavIconName } from "./AppNavIcon";

export type OptionCardIconName = AppNavIconName;

export type OptionCardItem = {
  id: string;
  title: string;
  description: string;
  to: string;
  icon: OptionCardIconName;
  ariaLabel?: string;
};

type OptionCardGridProps = {
  items: OptionCardItem[];
  ariaLabel: string;
  className?: string;
};

export default function OptionCardGrid({ items, ariaLabel, className }: OptionCardGridProps): JSX.Element {
  const gridClassName = className ? `option-card-grid ${className}` : "option-card-grid";

  return (
    <ul className={gridClassName} aria-label={ariaLabel}>
      {items.map((item) => (
        <li key={item.id} className="option-card">
          <Link className="option-card-link" to={item.to} aria-label={item.ariaLabel ?? item.title}>
            <div className="option-card-heading">
              <span className="option-card-icon" aria-hidden="true">
                <AppNavIcon name={item.icon} />
              </span>
              <h3 className="section-title">{item.title}</h3>
            </div>
            <p className="status-text">{item.description}</p>
          </Link>
        </li>
      ))}
    </ul>
  );
}
