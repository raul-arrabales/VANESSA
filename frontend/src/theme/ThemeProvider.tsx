import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  EDITABLE_COLOR_TOKENS,
  THEME_COLOR_OVERRIDES_STORAGE_KEY,
  THEME_FAMILIES,
  THEME_PRESETS,
  THEME_STORAGE_KEY,
  type StoredColorOverrides,
  type ThemeColorOverrides,
  type ThemeContextValue,
  type ThemeFamilyId,
  type ThemeId,
  getInitialTheme,
  getStoredColorOverrides,
  getThemeEffectiveColors,
  getThemeFamily,
  getThemeFamilyPresets,
  getThemePreset,
} from "./theme";

const ThemeContext = createContext<ThemeContextValue | null>(null);

type ThemeProviderProps = {
  children: ReactNode;
};

export function ThemeProvider({ children }: ThemeProviderProps): JSX.Element {
  const [theme, setThemeState] = useState<ThemeId>(() => getInitialTheme());
  const [allColorOverrides, setAllColorOverrides] = useState<StoredColorOverrides>(() => getStoredColorOverrides());

  const themePreset = useMemo(() => getThemePreset(theme), [theme]);
  const themeFamily = useMemo(() => getThemeFamily(themePreset.familyId), [themePreset.familyId]);
  const colorOverrides: ThemeColorOverrides = allColorOverrides[theme] ?? {};

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    document.documentElement.setAttribute("data-theme-family", themePreset.familyId);
    document.documentElement.style.colorScheme = themePreset.colorScheme;
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme, themePreset.colorScheme, themePreset.familyId]);

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
    themePreset,
    themeFamily,
    themeFamilies: THEME_FAMILIES,
    themePresets: THEME_PRESETS,
    colorOverrides,
    allColorOverrides,
    setTheme: (themeId: ThemeId) => {
      setThemeState(themeId);
    },
    getFamilyPresets: (familyId: ThemeFamilyId) => getThemeFamilyPresets(familyId),
    getEffectiveColors: (themeId: ThemeId) => getThemeEffectiveColors(themeId, allColorOverrides),
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
  }), [allColorOverrides, colorOverrides, theme, themeFamily, themePreset]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
}
