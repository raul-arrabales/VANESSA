import { Link } from "react-router-dom";

export type OptionCardIconName = "profile" | "approvals" | "health" | "userPage" | "adminPage" | "models";

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

const iconByName: Record<OptionCardIconName, JSX.Element> = {
  profile: (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path d="M12 12c2.76 0 5-2.24 5-5S14.76 2 12 2 7 4.24 7 7s2.24 5 5 5Zm0 2c-4.42 0-8 2.24-8 5v1h16v-1c0-2.76-3.58-5-8-5Z" />
    </svg>
  ),
  approvals: (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path d="m9.55 18.18-3.89-3.89 1.41-1.41 2.48 2.48 7.37-7.37 1.41 1.41-8.78 8.78ZM19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2Z" />
    </svg>
  ),
  health: (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path d="M3 13h4l2-4 3 8 2-4h7v-2h-6l-3 6-3-8-3 6H3v-2Z" />
    </svg>
  ),
  userPage: (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path d="M12 12c2.2 0 4-1.8 4-4s-1.8-4-4-4-4 1.8-4 4 1.8 4 4 4Zm0 2c-3.31 0-6 2.02-6 4.5V20h12v-1.5c0-2.48-2.69-4.5-6-4.5Z" />
    </svg>
  ),
  adminPage: (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path d="M12 2 3 6v6c0 5 3.84 9.74 9 11 5.16-1.26 9-6 9-11V6l-9-4Zm-1 14-3-3 1.41-1.41L11 13.17l3.59-3.59L16 11l-5 5Z" />
    </svg>
  ),
  models: (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path d="M4 6c0-1.1.9-2 2-2h12a2 2 0 0 1 2 2v2H4V6Zm0 4h16v4H4v-4Zm0 6h16v2a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-2Z" />
    </svg>
  ),
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
                {iconByName[item.icon]}
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
