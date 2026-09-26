import { useTranslation } from "react-i18next"

import { Appearance } from "@/components/Common/Appearance"
import { LanguageSwitcher } from "@/components/Common/LanguageSwitcher"
import { Logo } from "@/components/Common/Logo"
import { Footer } from "./Footer"

interface AuthLayoutProps {
  children: React.ReactNode
}

export function AuthLayout({ children }: AuthLayoutProps) {
  const { t } = useTranslation()

  return (
    <div className="grid min-h-svh lg:grid-cols-2">
      <div className="bg-primary-container text-on-primary-container relative hidden flex-col items-center justify-center gap-6 p-10 lg:flex">
        <div
          aria-hidden="true"
          className="bg-primary/20 absolute -top-24 -start-24 size-72 rounded-full"
        />
        <div
          aria-hidden="true"
          className="bg-primary/20 absolute -bottom-32 -end-16 size-96 rounded-full"
        />
        <Logo variant="full" className="z-10 h-14" asLink={false} />
        <p className="text-on-primary-container/80 z-10 max-w-xs text-center text-body-large">
          {t("auth.brandTagline")}
        </p>
      </div>
      <div className="bg-surface flex flex-col gap-4 p-6 md:p-10">
        <div className="flex justify-end gap-2">
          <LanguageSwitcher />
          <Appearance />
        </div>
        <div className="flex flex-1 items-center justify-center">
          <div className="w-full max-w-sm">{children}</div>
        </div>
        <Footer />
      </div>
    </div>
  )
}
