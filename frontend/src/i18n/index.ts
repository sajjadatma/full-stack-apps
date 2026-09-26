import i18n from "i18next"
import LanguageDetector from "i18next-browser-languagedetector"
import { initReactI18next } from "react-i18next"

import en from "./locales/en.json"
import fa from "./locales/fa.json"

declare module "i18next" {
  interface CustomTypeOptions {
    defaultNS: "translation"
    resources: {
      translation: typeof en
    }
  }
}

export const SUPPORTED_LANGUAGES = ["en", "fa"] as const
export type Language = (typeof SUPPORTED_LANGUAGES)[number]

export const DEFAULT_LANGUAGE: Language = "en"
export const LANGUAGE_STORAGE_KEY = "locale"

export function isRtlLanguage(language: string): boolean {
  return language.startsWith("fa")
}

export function normalizeLanguage(language?: string | null): Language {
  if (!language) return DEFAULT_LANGUAGE
  const base = language.split("-")[0]
  return (SUPPORTED_LANGUAGES as readonly string[]).includes(base)
    ? (base as Language)
    : DEFAULT_LANGUAGE
}

function applyDocumentLanguage(language: string): void {
  if (typeof document === "undefined") return
  const normalized = normalizeLanguage(language)
  document.documentElement.lang = normalized
  document.documentElement.dir = isRtlLanguage(normalized) ? "rtl" : "ltr"
}

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      fa: { translation: fa },
    },
    supportedLngs: [...SUPPORTED_LANGUAGES],
    fallbackLng: DEFAULT_LANGUAGE,
    interpolation: {
      escapeValue: false,
    },
    detection: {
      order: ["localStorage", "navigator"],
      lookupLocalStorage: LANGUAGE_STORAGE_KEY,
      caches: ["localStorage"],
      convertDetectedLanguage: (language: string) =>
        normalizeLanguage(language),
    },
    returnNull: false,
  })

applyDocumentLanguage(i18n.language)
i18n.on("languageChanged", applyDocumentLanguage)

export default i18n
