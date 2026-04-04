import type { AppNavIconName } from "../../components/AppNavIcon";

export type ShellNavItem = {
  id: string;
  label: string;
  to: string;
  icon: AppNavIconName;
  isActive: boolean;
};

export type TopBarPathItem = {
  id: string;
  label: string;
  to: string;
  isCurrent: boolean;
};

export type UserMenuItem = {
  id: string;
  label: string;
  to: string;
};
