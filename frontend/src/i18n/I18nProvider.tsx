import { DirectionProvider } from "@radix-ui/react-direction"
import type { ReactNode } from "react"

import { useLanguage } from "./useLanguage"

export function I18nProvider({ children }: { children: ReactNode }) {
  const { direction } = useLanguage()

  return <DirectionProvider dir={direction}>{children}</DirectionProvider>
}
