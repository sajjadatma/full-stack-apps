import { Briefcase, Home, ShieldCheck, Users } from "lucide-react"
import { useTranslation } from "react-i18next"

import { SidebarAppearance } from "@/components/Common/Appearance"
import { SidebarLanguageSwitcher } from "@/components/Common/LanguageSwitcher"
import { Logo } from "@/components/Common/Logo"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar"
import useAuth from "@/hooks/useAuth"
import { useLanguage } from "@/i18n/useLanguage"
import { type Item, Main } from "./Main"
import { User } from "./User"

export function AppSidebar() {
  const { user: currentUser, hasPermission } = useAuth()
  const { t } = useTranslation()
  const { direction } = useLanguage()

  const baseItems: Item[] = [
    { icon: Home, title: t("navigation.dashboard"), path: "/" },
    { icon: Briefcase, title: t("navigation.items"), path: "/items" },
  ]

  const items = [...baseItems]
  if (hasPermission("users.read")) {
    items.push({ icon: Users, title: t("navigation.admin"), path: "/admin" })
  }
  if (hasPermission("roles.read")) {
    items.push({
      icon: ShieldCheck,
      title: t("navigation.roles"),
      path: "/roles",
    })
  }

  return (
    <Sidebar collapsible="icon" side={direction === "rtl" ? "right" : "left"}>
      <SidebarHeader className="px-4 py-6 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:items-center">
        <Logo variant="responsive" />
      </SidebarHeader>
      <SidebarContent>
        <Main items={items} />
      </SidebarContent>
      <SidebarFooter>
        <SidebarAppearance />
        <SidebarLanguageSwitcher />
        <User user={currentUser} />
      </SidebarFooter>
    </Sidebar>
  )
}

export default AppSidebar
