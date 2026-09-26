import { useTranslation } from "react-i18next"

import { isRtlLanguage, type Language, normalizeLanguage } from "."

export function useLanguage() {
  const { i18n } = useTranslation()
  const language = normalizeLanguage(i18n.resolvedLanguage ?? i18n.language)
  const isRtl = isRtlLanguage(language)
  const direction: "ltr" | "rtl" = isRtl ? "rtl" : "ltr"

  const changeLanguage = (next: Language) => {
    if (next === language) return
    void i18n.changeLanguage(next)
  }

  return { language, isRtl, direction, changeLanguage }
}
