import { createFileRoute } from "@tanstack/react-router"
import { useTranslation } from "react-i18next"

import useAuth from "@/hooks/useAuth"
import i18n from "@/i18n"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
  head: () => ({
    meta: [
      {
        title: i18n.t("meta.dashboard"),
      },
    ],
  }),
})

function Dashboard() {
  const { user: currentUser } = useAuth()
  const { t } = useTranslation()

  const name = currentUser?.full_name || currentUser?.email || ""

  return (
    <div>
      <div>
        <h1 className="text-2xl truncate max-w-sm">
          {t("dashboard.greeting", { name })}
        </h1>
        <p className="text-muted-foreground">{t("dashboard.welcomeBack")}</p>
      </div>
    </div>
  )
}
