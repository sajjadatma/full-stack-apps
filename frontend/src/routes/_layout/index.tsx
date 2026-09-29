import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link as RouterLink } from "@tanstack/react-router"
import {
  AlertCircle,
  ChevronRight,
  History,
  LoaderCircle,
  Package,
  PanelsTopLeft,
  Users,
} from "lucide-react"
import { useTranslation } from "react-i18next"
import { DashboardService } from "@/client"
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
  const summaryQuery = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: async () => (await DashboardService.readDashboardSummary()).data,
    retry: false,
  })

  const name = currentUser?.full_name || currentUser?.email || ""
  const canReadProducts =
    hasPermission("products.read") || hasPermission("products.read_any")
  const canReadUsers = hasPermission("users.read")
  const canVisualize =
    hasPermission("generations.create") &&
    hasPermission("generations.read_own") &&
    canReadProducts
  const canReadGenerations =
    hasPermission("generations.read_own") ||
    hasPermission("generations.read_any")
  const summary = summaryQuery.data

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

      {summaryQuery.isPending && (
        <div className="grid min-h-24 place-items-center" role="status">
          <LoaderCircle className="size-7 animate-spin text-primary" />
          <span className="sr-only">{t("dashboard.loading")}</span>
        </div>
      )}
      {summaryQuery.isError && (
        <div
          className="flex items-center gap-2 rounded-xl border border-error p-4 text-on-surface"
          role="alert"
        >
          <AlertCircle className="size-5 text-error" />
          {t("dashboard.loadError")}
        </div>
      )}
      {summary && (
        <section
          className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
          aria-label={t("dashboard.metricsTitle")}
        >
          {summary.products && (
            <>
              <MetricCard
                label={t("dashboard.totalProducts")}
                value={summary.products.total_products}
                testId="metric-total-products"
                icon={Package}
              />
              <MetricCard
                label={t("dashboard.activeProducts")}
                value={summary.products.active_products}
                testId="metric-active-products"
                icon={Package}
              />
              <MetricCard
                label={t("dashboard.lowStockProducts")}
                value={summary.products.low_stock_products}
                testId="metric-low-stock-products"
                icon={AlertCircle}
              />
            </>
          )}
          {summary.generations && (
            <>
              <MetricCard
                label={t("dashboard.totalGenerations")}
                value={summary.generations.total}
                testId="metric-generations-total"
                icon={PanelsTopLeft}
              />
              <MetricCard
                label={t("dashboard.pendingGenerations")}
                value={summary.generations.pending}
                testId="metric-generations-pending"
                icon={History}
              />
              <MetricCard
                label={t("dashboard.processingGenerations")}
                value={summary.generations.processing}
                testId="metric-generations-processing"
                icon={History}
              />
              <MetricCard
                label={t("dashboard.completedGenerations")}
                value={summary.generations.completed}
                testId="metric-generations-completed"
                icon={History}
              />
              <MetricCard
                label={t("dashboard.failedGenerations")}
                value={summary.generations.failed}
                testId="metric-generations-failed"
                icon={AlertCircle}
              />
            </>
          )}
        </section>
      )}

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
            {canReadProducts && (
              <QuickLink
                to="/products"
                icon={Package}
                title={t("dashboard.productManagement")}
                description={t("dashboard.productManagementDescription")}
              />
            )}
            {canVisualize && (
              <QuickLink
                to="/visualizer"
                icon={PanelsTopLeft}
                title={t("navigation.visualizer")}
                description={t("dashboard.visualizerDescription")}
              />
            )}
            {canReadGenerations && (
              <QuickLink
                to="/generations"
                icon={History}
                title={t("navigation.generations")}
                description={t("dashboard.generationsDescription")}
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
  to: "/products" | "/visualizer" | "/generations" | "/admin"
  icon: React.ComponentType<{ className?: string }>
  title: string
  description: string
}

function MetricCard({
  label,
  value,
  testId,
  icon: Icon,
}: {
  label: string
  value: number
  testId: string
  icon: React.ComponentType<{ className?: string }>
}) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-label-large text-on-surface-variant">
          {label}
        </CardTitle>
        <Icon className="size-5 text-primary" />
      </CardHeader>
      <CardContent>
        <p
          className="text-headline-medium text-on-surface"
          data-testid={testId}
        >
          {value.toLocaleString()}
        </p>
      </CardContent>
    </Card>
  )
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
