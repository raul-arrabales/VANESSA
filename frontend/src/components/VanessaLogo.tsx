type VanessaLogoProps = {
  className?: string;
  size?: number;
};

export default function VanessaLogo({ className, size = 56 }: VanessaLogoProps): JSX.Element {
  return (
    <svg
      className={className}
      data-testid="app-logo"
      aria-hidden="true"
      focusable="false"
      viewBox="0 0 64 64"
      width={size}
      height={size}
      fill="none"
    >
      <path
        className="vanessa-logo__halo"
        d="M32 8L48.5 16.5L56 32L48.5 47.5L32 56L15.5 47.5L8 32L15.5 16.5Z"
      />
      <path
        className="vanessa-logo__orbit"
        d="M16.5 24.5L32 14.5L47.5 24.5"
      />
      <path
        className="vanessa-logo__orbit"
        d="M16.5 39.5L32 49.5L47.5 39.5"
      />
      <path
        className="vanessa-logo__orbit"
        d="M18.8 21.2L32 12.8L45.2 21.2"
      />
      <path
        className="vanessa-logo__orbit"
        d="M18.8 42.8L32 51.2L45.2 42.8"
      />
      <path
        className="vanessa-logo__vector"
        d="M32 17.5L41 26L32 44.5L23 26Z"
      />
      <path
        className="vanessa-logo__vector"
        d="M23 26H41"
      />
      <circle className="vanessa-logo__core" cx="32" cy="32" r="4.2" />
    </svg>
  );
}
