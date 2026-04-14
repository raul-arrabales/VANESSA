export type AppNavIconName =
  | "home"
  | "profile"
  | "register"
  | "vanessa"
  | "approvals"
  | "health"
  | "settings"
  | "userPage"
  | "adminPage"
  | "models"
  | "ai";

type AppNavIconProps = {
  name: AppNavIconName;
};

const iconByName: Record<AppNavIconName, JSX.Element> = {
  home: (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-4.5v-6h-5v6H5a1 1 0 0 1-1-1v-9.5Z" />
    </svg>
  ),
  profile: (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path d="M12 12c2.76 0 5-2.24 5-5S14.76 2 12 2 7 4.24 7 7s2.24 5 5 5Zm0 2c-4.42 0-8 2.24-8 5v1h16v-1c0-2.76-3.58-5-8-5Z" />
    </svg>
  ),
  register: (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path d="M15 8a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm-3 5c-3.31 0-6 1.79-6 4v1h7v-2.5c0-.92.27-1.78.73-2.5H12Zm6 0v2h2v2h-2v2h-2v-2h-2v-2h2v-2h2Z" />
    </svg>
  ),
  vanessa: (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path d="M4 5h3.1L12 16.36 16.9 5H20l-6.62 14h-2.76L4 5Z" />
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
  settings: (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path d="M19.43 12.98c.04-.32.07-.65.07-.98s-.02-.66-.07-.98l2.11-1.65-2-3.46-2.49 1a7.18 7.18 0 0 0-1.69-.98L15 3.29h-4l-.36 2.64c-.6.24-1.16.57-1.69.98l-2.49-1-2 3.46 2.11 1.65c-.05.32-.07.65-.07.98s.02.66.07.98l-2.11 1.65 2 3.46 2.49-1c.53.41 1.09.74 1.69.98L11 20.71h4l.36-2.64c.6-.24 1.16-.57 1.69-.98l2.49 1 2-3.46-2.11-1.65ZM13 15.5a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7Z" />
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
  ai: (
    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
      <path d="M12 2a3 3 0 0 1 3 3v1h1.5A2.5 2.5 0 0 1 19 8.5V10h1a2 2 0 1 1 0 4h-1v1.5A2.5 2.5 0 0 1 16.5 18H15v1a3 3 0 1 1-6 0v-1H7.5A2.5 2.5 0 0 1 5 15.5V14H4a2 2 0 1 1 0-4h1V8.5A2.5 2.5 0 0 1 7.5 6H9V5a3 3 0 0 1 3-3Zm-1 4H9v2h2V6Zm4 0h-2v2h2V6Zm-3 5a2 2 0 1 0 0 4 2 2 0 0 0 0-4Zm-5 1H8v3h3.5a3.97 3.97 0 0 1-.5-2c0-.36.05-.7.14-1H11Zm5.5 0c.09.3.14.64.14 1 0 .74-.2 1.41-.54 2H16v-3h-1.5Z" />
    </svg>
  ),
};

export default function AppNavIcon({ name }: AppNavIconProps): JSX.Element {
  return iconByName[name];
}
