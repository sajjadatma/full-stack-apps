import { createFileRoute, Link as RouterLink } from "@tanstack/react-router"
import { Briefcase, ChevronRight, Users } from "lucide-react"
import { useTranslation } from "react-i18next"

import { roleLabel } from "@/components/Admin/roleLabel"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import useAuth from "@/hooks/useAuth"
import i18n from "@/i18n"
import { getInitials } from "@/utils"

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
  const { user: currentUser, hasPermission } = useAuth()
  const { t } = useTranslation()

  const name = currentUser?.full_name || currentUser?.email || ""
  const canReadItems =
    hasPermission("items.read_any") || hasPermission("items.read_own")
  const canReadUsers = hasPermission("users.read")

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-headline-small text-on-surface">
          {t("dashboard.greeting", { name })}
        </h1>
        <p className="text-body-medium text-on-surface-variant">
          {t("dashboard.welcomeBack")}
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>{t("dashboard.accountTitle")}</CardTitle>
            <CardDescription>{t("dashboard.signedInAs")}</CardDescription>
          </CardHeader>
          <CardContent className="flex items-center gap-4">
            <Avatar className="size-12">
              <AvatarFallback className="bg-primary text-on-primary text-title-medium">
                {getInitials(name)}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0">
              <p className="text-title-medium text-on-surface truncate">
                {currentUser?.full_name || t("common.na")}
              </p>
              <p className="text-body-medium text-on-surface-variant truncate">
                {currentUser?.email}
              </p>
              {currentUser?.role && (
                <Badge variant="secondary" className="mt-2">
                  {roleLabel(currentUser.role, t)}
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>{t("dashboard.quickLinksTitle")}</CardTitle>
            <CardDescription>
              {t("dashboard.quickLinksSubtitle")}
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            {canReadItems && (
              <QuickLink
                to="/items"
                icon={Briefcase}
                title={t("navigation.items")}
                description={t("dashboard.itemsCardDescription")}
              />
            )}
            {canReadUsers && (
              <QuickLink
                to="/admin"
                icon={Users}
                title={t("navigation.admin")}
                description={t("dashboard.adminCardDescription")}
              />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

interface QuickLinkProps {
  to: "/items" | "/admin"
  icon: React.ComponentType<{ className?: string }>
  title: string
  description: string
}

function QuickLink({ to, icon: Icon, title, description }: QuickLinkProps) {
  return (
    <RouterLink
      to={to}
      className="hover:bg-on-surface/5 group flex items-start gap-3 rounded-lg border border-outline-variant p-4 transition-colors"
    >
      <span className="bg-secondary-container text-on-secondary-container rounded-full p-2">
        <Icon className="size-5" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="text-title-medium text-on-surface block">{title}</span>
        <span className="text-body-medium text-on-surface-variant block">
          {description}
        </span>
      </span>
      <ChevronRight className="text-on-surface-variant mt-1 size-5 shrink-0 rtl:rotate-180" />
    </RouterLink>
  )
}
