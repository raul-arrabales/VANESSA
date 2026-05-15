import type { ButtonHTMLAttributes, ReactNode } from "react";

type IconButtonProps = {
  label: string;
  children: ReactNode;
  tone?: "default" | "danger";
} & Omit<ButtonHTMLAttributes<HTMLButtonElement>, "aria-label" | "title" | "children">;

export default function IconButton({
  label,
  children,
  tone = "default",
  className,
  type = "button",
  ...buttonProps
}: IconButtonProps): JSX.Element {
  const classes = ["icon-button", tone === "danger" ? "icon-button-danger" : "", className ?? ""]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      {...buttonProps}
      type={type}
      className={classes}
      aria-label={label}
      title={label}
    >
      {children}
    </button>
  );
}
