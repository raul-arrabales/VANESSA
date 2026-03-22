import { createInstance } from "i18next";
import { initReactI18next } from "react-i18next";
import enCommon from "../i18n/locales/en/common.json";
import esCommon from "../i18n/locales/es/common.json";

export const testI18n = createInstance();

let initializationPromise: Promise<unknown> | null = null;

export function ensureTestI18n(): Promise<typeof testI18n> {
  if (!initializationPromise) {
    initializationPromise = testI18n.use(initReactI18next).init({
      lng: "en",
      fallbackLng: "en",
      showSupportNotice: false,
      supportedLngs: ["en", "es"],
      ns: ["common"],
      defaultNS: "common",
      interpolation: {
        escapeValue: false,
      },
      resources: {
        en: {
          common: enCommon,
        },
        es: {
          common: esCommon,
        },
      },
      react: {
        useSuspense: false,
      },
    });
  }

  return initializationPromise.then(() => testI18n);
}
