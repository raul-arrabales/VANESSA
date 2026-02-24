export const THEME_STORAGE_KEY = "vanessa.theme";
export const THEME_COLOR_OVERRIDES_STORAGE_KEY = "vanessa.theme.color-overrides";
export const EDITABLE_COLOR_TOKENS = [
  "--bg-canvas",
  "--bg-surface",
  "--bg-subtle",
  "--text-primary",
  "--text-secondary",
  "--accent-primary",
  "--accent-secondary",
  "--border-muted",
  "--status-success",
  "--status-error",
  "--lcars-rail",
] as const;

export type ThemeMode = "light" | "dark";

export type ThemeContextValue = {
  theme: ThemeMode;
  colorOverrides: Partial<Record<string, string>>;
  setTheme: (mode: ThemeMode) => void;
  toggleTheme: () => void;
  applyColorOverrides: (nextOverrides: Partial<Record<string, string>>) => void;
  resetColorOverrides: () => void;
};

const THEME_MODES: ThemeMode[] = ["light", "dark"];

export function isThemeMode(value: string | null | undefined): value is ThemeMode {
  if (!value) {
    return false;
  }
  return THEME_MODES.includes(value as ThemeMode);
}

export function resolveInitialTheme(
  storedTheme: string | null,
  prefersDark: boolean,
): ThemeMode {
  if (isThemeMode(storedTheme)) {
    return storedTheme;
  }
  return prefersDark ? "dark" : "light";
}

export function getSystemPrefersDark(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function getStoredTheme(): ThemeMode | null {
  if (typeof window === "undefined") {
    return null;
  }
  const value = window.localStorage.getItem(THEME_STORAGE_KEY);
  return isThemeMode(value) ? value : null;
}

export function getInitialTheme(): ThemeMode {
  return resolveInitialTheme(getStoredTheme(), getSystemPrefersDark());
}

export function getToggledTheme(theme: ThemeMode): ThemeMode {
  return theme === "light" ? "dark" : "light";
}

type StoredColorOverrides = Partial<Record<ThemeMode, Partial<Record<string, string>>>>;

export function getStoredColorOverrides(): StoredColorOverrides {
  if (typeof window === "undefined") {
    return {};
  }

  const rawValue = window.localStorage.getItem(THEME_COLOR_OVERRIDES_STORAGE_KEY);
  if (!rawValue) {
    return {};
  }

  try {
    const parsed = JSON.parse(rawValue);
    if (!parsed || typeof parsed !== "object") {
      return {};
    }
    return parsed as StoredColorOverrides;
  } catch {
    return {};
  }
}
