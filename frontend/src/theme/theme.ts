export const THEME_STORAGE_KEY = "vanessa.theme";

export type ThemeMode = "light" | "dark";

export type ThemeContextValue = {
  theme: ThemeMode;
  setTheme: (mode: ThemeMode) => void;
  toggleTheme: () => void;
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
