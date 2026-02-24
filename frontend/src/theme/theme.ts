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

export type EditableColorToken = typeof EDITABLE_COLOR_TOKENS[number];
export type ThemeColors = Record<EditableColorToken, string>;
export type ThemeMode = "light" | "dark";
export type ThemeColorOverrides = Partial<Record<EditableColorToken, string>>;
export type StoredColorOverrides = Partial<Record<ThemeMode, ThemeColorOverrides>>;

export type ThemeContextValue = {
  theme: ThemeMode;
  colorOverrides: ThemeColorOverrides;
  allColorOverrides: StoredColorOverrides;
  setTheme: (mode: ThemeMode) => void;
  toggleTheme: () => void;
  getEffectiveColors: (mode: ThemeMode) => ThemeColors;
  applyColorOverrides: (nextOverrides: ThemeColorOverrides) => void;
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

export const DEFAULT_THEME_COLORS: Record<ThemeMode, ThemeColors> = {
  light: {
    "--bg-canvas": "#ecf3fb",
    "--bg-surface": "#f9fbff",
    "--bg-subtle": "#e5edf8",
    "--text-primary": "#0f213a",
    "--text-secondary": "#385172",
    "--accent-primary": "#0f62fe",
    "--accent-secondary": "#1f7a99",
    "--border-muted": "#bfd0e6",
    "--status-success": "#0f7a3d",
    "--status-error": "#b42318",
    "--lcars-rail": "#f0a358",
  },
  dark: {
    "--bg-canvas": "#08111e",
    "--bg-surface": "#101c2d",
    "--bg-subtle": "#16263a",
    "--text-primary": "#e3eefc",
    "--text-secondary": "#aac0dd",
    "--accent-primary": "#78b3ff",
    "--accent-secondary": "#73d1f1",
    "--border-muted": "#30455f",
    "--status-success": "#4bd58f",
    "--status-error": "#ff8b87",
    "--lcars-rail": "#ffb56f",
  },
};

export function getThemeBaseColors(theme: ThemeMode): ThemeColors {
  return DEFAULT_THEME_COLORS[theme];
}

export function getThemeEffectiveColors(
  theme: ThemeMode,
  allOverrides: StoredColorOverrides,
): ThemeColors {
  return {
    ...getThemeBaseColors(theme),
    ...(allOverrides[theme] ?? {}),
  };
}

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
