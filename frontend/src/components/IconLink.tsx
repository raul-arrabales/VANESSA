import type { ReactNode } from "react";
import { Link, type LinkProps } from "react-router-dom";

type IconLinkProps = {
  label: string;
  children: ReactNode;
  tone?: "default" | "danger";
} & Omit<LinkProps, "aria-label" | "title" | "children">;

export default function IconLink({
  label,
  children,
  tone = "default",
  className,
  ...linkProps
}: IconLinkProps): JSX.Element {
  const classes = ["icon-button", tone === "danger" ? "icon-button-danger" : "", className ?? ""]
    .filter(Boolean)
    .join(" ");

  return (
    <Link
      {...linkProps}
      className={classes}
      aria-label={label}
      title={label}
    >
      {children}
    </Link>
  );
}
