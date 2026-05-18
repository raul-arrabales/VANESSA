import type { HTMLAttributes, ReactNode } from "react";

function classes(...values: Array<string | undefined>): string {
  return values.filter(Boolean).join(" ");
}

type CompactRegistryListProps = {
  children: ReactNode;
  ariaLabel?: string;
  className?: string;
};

export function CompactRegistryList({
  children,
  ariaLabel,
  className,
}: CompactRegistryListProps): JSX.Element {
  return (
    <div className={classes("compact-registry-list", className)} role="list" aria-label={ariaLabel}>
      {children}
    </div>
  );
}

type CompactRegistryItemProps = {
  children: ReactNode;
  className?: string;
} & HTMLAttributes<HTMLElement>;

export function CompactRegistryItem({
  children,
  className,
  ...itemProps
}: CompactRegistryItemProps): JSX.Element {
  return (
    <article {...itemProps} className={classes("compact-registry-item", className)} role="listitem">
      {children}
    </article>
  );
}

export function CompactRegistryMain({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}): JSX.Element {
  return <div className={classes("compact-registry-main", className)}>{children}</div>;
}

export function CompactRegistryHeading({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}): JSX.Element {
  return <div className={classes("compact-registry-heading", className)}>{children}</div>;
}

export function CompactRegistryMeta({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}): JSX.Element {
  return <div className={classes("compact-registry-meta", className)}>{children}</div>;
}

export function CompactRegistryActions({
  children,
  label,
  className,
}: {
  children: ReactNode;
  label?: string;
  className?: string;
}): JSX.Element {
  return (
    <div className={classes("compact-registry-actions", className)} role={label ? "group" : undefined} aria-label={label}>
      {children}
    </div>
  );
}

export function CompactRegistryDescription({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}): JSX.Element {
  return <p className={classes("status-text compact-registry-description", className)}>{children}</p>;
}

export function CompactRegistryProgress({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}): JSX.Element {
  return <div className={classes("compact-registry-progress", className)}>{children}</div>;
}
