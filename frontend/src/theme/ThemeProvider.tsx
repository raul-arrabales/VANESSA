import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  EDITABLE_COLOR_TOKENS,
  THEME_COLOR_OVERRIDES_STORAGE_KEY,
  THEME_STORAGE_KEY,
  type StoredColorOverrides,
  type ThemeColorOverrides,
  type ThemeContextValue,
  type ThemeMode,
  getThemeEffectiveColors,
  getInitialTheme,
  getStoredColorOverrides,
  getToggledTheme,
} from "./theme";

const ThemeContext = createContext<ThemeContextValue | null>(null);

type ThemeProviderProps = {
  children: ReactNode;
};

export function ThemeProvider({ children }: ThemeProviderProps): JSX.Element {
  const [theme, setThemeState] = useState<ThemeMode>(() => getInitialTheme());
  const [allColorOverrides, setAllColorOverrides] = useState<StoredColorOverrides>(() => getStoredColorOverrides());

  const colorOverrides: ThemeColorOverrides = allColorOverrides[theme] ?? {};

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    document.documentElement.style.colorScheme = theme;
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  useEffect(() => {
    EDITABLE_COLOR_TOKENS.forEach((token) => {
      document.documentElement.style.removeProperty(token);
    });

    Object.entries(colorOverrides).forEach(([token, value]) => {
      if (value) {
        document.documentElement.style.setProperty(token, value);
      }
    });
  }, [colorOverrides]);

  useEffect(() => {
    window.localStorage.setItem(THEME_COLOR_OVERRIDES_STORAGE_KEY, JSON.stringify(allColorOverrides));
  }, [allColorOverrides]);

  const value = useMemo<ThemeContextValue>(() => ({
    theme,
    colorOverrides,
    allColorOverrides,
    setTheme: (mode: ThemeMode) => {
      setThemeState(mode);
    },
    toggleTheme: () => {
      setThemeState((current) => getToggledTheme(current));
    },
    getEffectiveColors: (mode: ThemeMode) => getThemeEffectiveColors(mode, allColorOverrides),
    applyColorOverrides: (nextOverrides: ThemeColorOverrides) => {
      setAllColorOverrides((currentOverrides) => ({
        ...currentOverrides,
        [theme]: nextOverrides,
      }));
    },
    resetColorOverrides: () => {
      setAllColorOverrides((currentOverrides) => ({
        ...currentOverrides,
        [theme]: {},
      }));
    },
  }), [allColorOverrides, colorOverrides, theme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
}
