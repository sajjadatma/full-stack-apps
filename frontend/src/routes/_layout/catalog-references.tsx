import { createFileRoute, redirect } from "@tanstack/react-router"
import { FolderTree, Tag } from "lucide-react"
import { useTranslation } from "react-i18next"

import { UsersService } from "@/client"
import { ReferenceManager } from "@/components/CatalogReferences/ReferenceManager"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useAuth from "@/hooks/useAuth"
import i18n from "@/i18n"

export const Route = createFileRoute("/_layout/catalog-references")({
  component: CatalogReferencesPage,
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    const permissions = user.permissions ?? []
    const canRead =
      permissions.includes("products.read") ||
      permissions.includes("products.read_any")
    const canManage = [
      "products.create",
      "products.update",
      "products.delete",
    ].some((permission) => permissions.includes(permission))
    if (!canRead || !canManage) throw redirect({ to: "/" })
  },
  head: () => ({ meta: [{ title: i18n.t("meta.catalogReferences") }] }),
})

function CatalogReferencesPage() {
  const { t } = useTranslation()
  const { hasPermission } = useAuth()
  const canCreate = hasPermission("products.create")
  const canUpdate = hasPermission("products.update")
  const canDelete = hasPermission("products.delete")

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-headline-small text-on-surface">
          {t("catalogReferences.title")}
        </h1>
        <p className="mt-1 text-body-medium text-on-surface-variant">
          {t("catalogReferences.subtitle")}
        </p>
      </header>
      <Tabs defaultValue="categories">
        <TabsList aria-label={t("catalogReferences.tabs")}>
          <TabsTrigger value="categories">
            <FolderTree />
            {t("catalogReferences.categories")}
          </TabsTrigger>
          <TabsTrigger value="brands">
            <Tag />
            {t("catalogReferences.brands")}
          </TabsTrigger>
        </TabsList>
        <TabsContent value="categories">
          <ReferenceManager
            kind="category"
            canCreate={canCreate}
            canUpdate={canUpdate}
            canDelete={canDelete}
          />
        </TabsContent>
        <TabsContent value="brands">
          <ReferenceManager
            kind="brand"
            canCreate={canCreate}
            canUpdate={canUpdate}
            canDelete={canDelete}
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}
