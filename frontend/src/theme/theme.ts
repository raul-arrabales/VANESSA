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
export type ThemeColorOverrides = Partial<Record<EditableColorToken, string>>;

export const THEME_FAMILIES = [
  {
    id: "default",
    titleKey: "theme.families.default.title",
    descriptionKey: "theme.families.default.description",
  },
  {
    id: "retro",
    titleKey: "theme.families.retro.title",
    descriptionKey: "theme.families.retro.description",
  },
] as const;

export type ThemeFamilyId = typeof THEME_FAMILIES[number]["id"];
export type ThemeColorScheme = "light" | "dark";

export type ThemeFamilyDefinition = {
  id: ThemeFamilyId;
  titleKey: string;
  descriptionKey: string;
};

export type ThemePresetDefinitionBase<Id extends string = string> = {
  id: Id;
  familyId: ThemeFamilyId;
  presetId: string;
  titleKey: string;
  descriptionKey: string;
  colorScheme: ThemeColorScheme;
  colors: ThemeColors;
};

export const THEME_PRESETS = [
  {
    id: "default-day",
    familyId: "default",
    presetId: "day",
    titleKey: "theme.presets.defaultDay.title",
    descriptionKey: "theme.presets.defaultDay.description",
    colorScheme: "light",
    colors: {
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
  },
  {
    id: "default-night",
    familyId: "default",
    presetId: "night",
    titleKey: "theme.presets.defaultNight.title",
    descriptionKey: "theme.presets.defaultNight.description",
    colorScheme: "dark",
    colors: {
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
  },
  {
    id: "retro-terminal",
    familyId: "retro",
    presetId: "terminal",
    titleKey: "theme.presets.retroTerminal.title",
    descriptionKey: "theme.presets.retroTerminal.description",
    colorScheme: "dark",
    colors: {
      "--bg-canvas": "#08140d",
      "--bg-surface": "#0d1c13",
      "--bg-subtle": "#11281b",
      "--text-primary": "#d7ffd7",
      "--text-secondary": "#8fd8a5",
      "--accent-primary": "#63f59b",
      "--accent-secondary": "#f4b860",
      "--border-muted": "#2f6c49",
      "--status-success": "#7dffa9",
      "--status-error": "#ff9c6e",
      "--lcars-rail": "#f0a93d",
    },
  },
] as const satisfies readonly ThemePresetDefinitionBase[];

export type ThemeId = typeof THEME_PRESETS[number]["id"];
export type ThemePresetDefinition = ThemePresetDefinitionBase<ThemeId>;
export type StoredColorOverrides = Partial<Record<ThemeId, ThemeColorOverrides>>;

export type ThemeContextValue = {
  theme: ThemeId;
  themePreset: ThemePresetDefinition;
  themeFamily: ThemeFamilyDefinition;
  themeFamilies: readonly ThemeFamilyDefinition[];
  themePresets: readonly ThemePresetDefinition[];
  colorOverrides: ThemeColorOverrides;
  allColorOverrides: StoredColorOverrides;
  setTheme: (themeId: ThemeId) => void;
  getFamilyPresets: (familyId: ThemeFamilyId) => ThemePresetDefinition[];
  getEffectiveColors: (themeId: ThemeId) => ThemeColors;
  applyColorOverrides: (nextOverrides: ThemeColorOverrides) => void;
  resetColorOverrides: () => void;
};

export const DEFAULT_DAY_THEME_ID: ThemeId = "default-day";
export const DEFAULT_NIGHT_THEME_ID: ThemeId = "default-night";

const LEGACY_THEME_ALIASES: Record<string, ThemeId> = {
  light: DEFAULT_DAY_THEME_ID,
  dark: DEFAULT_NIGHT_THEME_ID,
};

const THEME_ID_SET = new Set<string>(THEME_PRESETS.map((preset) => preset.id));
const THEME_PRESET_BY_ID = Object.fromEntries(
  THEME_PRESETS.map((preset) => [preset.id, preset]),
) as Record<ThemeId, ThemePresetDefinition>;
const THEME_FAMILY_BY_ID = Object.fromEntries(
  THEME_FAMILIES.map((family) => [family.id, family]),
) as Record<ThemeFamilyId, ThemeFamilyDefinition>;
const EDITABLE_COLOR_TOKEN_SET = new Set<string>(EDITABLE_COLOR_TOKENS);

export function isThemeId(value: string | null | undefined): value is ThemeId {
  if (!value) {
    return false;
  }
  return THEME_ID_SET.has(value);
}

export function normalizeStoredTheme(value: string | null | undefined): ThemeId | null {
  if (!value) {
    return null;
  }
  if (isThemeId(value)) {
    return value;
  }
  return LEGACY_THEME_ALIASES[value] ?? null;
}

export function getThemePreset(themeId: ThemeId): ThemePresetDefinition {
  return THEME_PRESET_BY_ID[themeId];
}

export function getThemeFamily(familyId: ThemeFamilyId): ThemeFamilyDefinition {
  return THEME_FAMILY_BY_ID[familyId];
}

export function getThemeFamilyPresets(familyId: ThemeFamilyId): ThemePresetDefinition[] {
  return THEME_PRESETS.filter((preset) => preset.familyId === familyId);
}

export function getDefaultThemeId(prefersDark = false): ThemeId {
  return prefersDark ? DEFAULT_NIGHT_THEME_ID : DEFAULT_DAY_THEME_ID;
}

export function resolveInitialTheme(
  storedTheme: string | null,
  prefersDark: boolean,
): ThemeId {
  return normalizeStoredTheme(storedTheme) ?? getDefaultThemeId(prefersDark);
}

export function getSystemPrefersDark(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function getStoredTheme(): ThemeId | null {
  if (typeof window === "undefined") {
    return null;
  }
  return normalizeStoredTheme(window.localStorage.getItem(THEME_STORAGE_KEY));
}

export function getInitialTheme(): ThemeId {
  return resolveInitialTheme(getStoredTheme(), getSystemPrefersDark());
}

export function getThemeBaseColors(themeId: ThemeId): ThemeColors {
  return getThemePreset(themeId).colors;
}

export function getThemeEffectiveColors(
  themeId: ThemeId,
  allOverrides: StoredColorOverrides,
): ThemeColors {
  return {
    ...getThemeBaseColors(themeId),
    ...(allOverrides[themeId] ?? {}),
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function sanitizeThemeColorOverrides(value: unknown): ThemeColorOverrides {
  if (!isRecord(value)) {
    return {};
  }

  const sanitizedEntries = Object.entries(value).filter(([token, colorValue]) => (
    EDITABLE_COLOR_TOKEN_SET.has(token)
      && typeof colorValue === "string"
      && colorValue.trim().length > 0
  ));

  return Object.fromEntries(sanitizedEntries) as ThemeColorOverrides;
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
    const parsed = JSON.parse(rawValue) as unknown;
    if (!isRecord(parsed)) {
      return {};
    }

    const nextOverrides: StoredColorOverrides = {};
    Object.entries(parsed).forEach(([storedThemeId, overrideValue]) => {
      const normalizedThemeId = normalizeStoredTheme(storedThemeId);
      if (!normalizedThemeId) {
        return;
      }

      nextOverrides[normalizedThemeId] = {
        ...(nextOverrides[normalizedThemeId] ?? {}),
        ...sanitizeThemeColorOverrides(overrideValue),
      };
    });

    return nextOverrides;
  } catch {
    return {};
  }
}
