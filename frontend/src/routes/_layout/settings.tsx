import { createFileRoute } from "@tanstack/react-router"
import { useTranslation } from "react-i18next"

import ChangePassword from "@/components/UserSettings/ChangePassword"
import DeleteAccount from "@/components/UserSettings/DeleteAccount"
import UserInformation from "@/components/UserSettings/UserInformation"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useAuth from "@/hooks/useAuth"
import i18n from "@/i18n"

export const Route = createFileRoute("/_layout/settings")({
  component: UserSettings,
  head: () => ({
    meta: [
      {
        title: i18n.t("meta.settings"),
      },
    ],
  }),
})

function UserSettings() {
  const { user: currentUser, hasPermission } = useAuth()
  const { t } = useTranslation()

  if (!currentUser) {
    return null
  }

  const tabsConfig = [
    {
      value: "my-profile",
      title: t("settings.tabs.profile"),
      component: UserInformation,
    },
    {
      value: "password",
      title: t("settings.tabs.password"),
      component: ChangePassword,
    },
    {
      value: "danger-zone",
      title: t("settings.tabs.danger"),
      component: DeleteAccount,
    },
  ]

  const finalTabs = tabsConfig.filter((tab) => {
    if (tab.value === "my-profile") return hasPermission("users.update_self")
    if (tab.value === "password") return hasPermission("users.update_self")
    if (tab.value === "danger-zone") return hasPermission("users.delete_self")
    return false
  })

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          {t("settings.title")}
        </h1>
        <p className="text-muted-foreground">{t("settings.subtitle")}</p>
      </div>

      <Tabs defaultValue="my-profile">
        <TabsList>
          {finalTabs.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value}>
              {tab.title}
            </TabsTrigger>
          ))}
        </TabsList>
        {finalTabs.map((tab) => (
          <TabsContent key={tab.value} value={tab.value}>
            <tab.component />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}
