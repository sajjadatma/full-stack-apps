import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Search } from "lucide-react"
import { Suspense } from "react"
import { useTranslation } from "react-i18next"

import { ItemsService, UsersService } from "@/client"
import { DataTable } from "@/components/Common/DataTable"
import AddItem from "@/components/Items/AddItem"
import { useItemColumns } from "@/components/Items/columns"
import PendingItems from "@/components/Pending/PendingItems"
import useAuth from "@/hooks/useAuth"
import i18n from "@/i18n"

function getItemsQueryOptions() {
  return {
    queryFn: async () =>
      (await ItemsService.readItems({ query: { skip: 0, limit: 100 } })).data,
    queryKey: ["items"],
  }
}

export const Route = createFileRoute("/_layout/items")({
  component: Items,
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    const canReadItems =
      user.permissions?.includes("items.read_any") ||
      user.permissions?.includes("items.read_own")
    if (!canReadItems) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [
      {
        title: i18n.t("meta.items"),
      },
    ],
  }),
})

function ItemsTableContent() {
  const { data: items } = useSuspenseQuery(getItemsQueryOptions())
  const { t } = useTranslation()
  const columns = useItemColumns()

  if (items.data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Search className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">{t("items.emptyTitle")}</h3>
        <p className="text-muted-foreground">{t("items.emptySubtitle")}</p>
      </div>
    )
  }

  return <DataTable columns={columns} data={items.data} />
}

function ItemsTable() {
  return (
    <Suspense fallback={<PendingItems />}>
      <ItemsTableContent />
    </Suspense>
  )
}

function Items() {
  const { t } = useTranslation()
  const { hasPermission } = useAuth()

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {t("items.title")}
          </h1>
          <p className="text-muted-foreground">{t("items.subtitle")}</p>
        </div>
        {hasPermission("items.create") && <AddItem />}
      </div>
      <ItemsTable />
    </div>
  )
}
