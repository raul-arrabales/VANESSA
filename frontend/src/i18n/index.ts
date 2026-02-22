import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import resourcesToBackend from "i18next-resources-to-backend";
import type { ResourceKey } from "i18next";
import { initReactI18next } from "react-i18next";

const isDev = import.meta.env.DEV;
const localeLoaders = import.meta.glob("./locales/*/*.json");

void i18n
  .use(
    resourcesToBackend(async (language: string, namespace: string): Promise<ResourceKey> => {
      const key = `./locales/${language}/${namespace}.json`;
      const loader = localeLoaders[key];
      if (!loader) {
        throw new Error(`Missing locale bundle for ${language}/${namespace}`);
      }
      const localeModule = (await loader()) as { default: ResourceKey };
      return localeModule.default;
    }),
  )
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: "en",
    supportedLngs: ["en", "es"],
    nonExplicitSupportedLngs: true,
    ns: ["common"],
    defaultNS: "common",
    interpolation: {
      escapeValue: false,
    },
    debug: isDev,
    detection: {
      order: ["localStorage", "navigator"],
      lookupLocalStorage: "vanessa.locale",
      caches: ["localStorage"],
    },
    parseMissingKeyHandler: (key: string) => {
      if (isDev) {
        console.warn(`[i18n] missing translation key: ${key}`);
      }
      return key;
    },
    react: {
      useSuspense: false,
    },
  });

export default i18n;
