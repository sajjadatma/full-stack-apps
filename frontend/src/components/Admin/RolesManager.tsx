import { useQuery } from "@tanstack/react-query"
import type { ColumnDef } from "@tanstack/react-table"
import { EllipsisVertical } from "lucide-react"
import { useMemo } from "react"
import { useTranslation } from "react-i18next"

import { type PermissionPublic, type RolePublic, RolesService } from "@/client"
import { DataTable } from "@/components/Common/DataTable"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import useAuth from "@/hooks/useAuth"
import DeleteRole from "./DeleteRole"
import RoleForm from "./RoleForm"
import { roleLabel } from "./roleLabel"

function RoleRowActions({
  role,
  permissions,
}: {
  role: RolePublic
  permissions: PermissionPublic[]
}) {
  const { hasPermission } = useAuth()
  const canUpdate = hasPermission("roles.update")
  const canDelete = hasPermission("roles.delete")

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <EllipsisVertical />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {canUpdate && <RoleForm role={role} permissions={permissions} />}
        {canDelete && <DeleteRole role={role} onSuccess={() => {}} />}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

function useRoleColumns(permissions: PermissionPublic[]) {
  const { t } = useTranslation()
  const { hasPermission } = useAuth()

  return useMemo<ColumnDef<RolePublic>[]>(
    () => [
      {
        accessorKey: "name",
        header: t("roles.name"),
        cell: ({ row }) => (
          <div className="flex items-center gap-2">
            <span className="font-medium">{roleLabel(row.original, t)}</span>
            {row.original.is_system && (
              <Badge variant="outline" className="text-xs">
                {t("roles.systemRole")}
              </Badge>
            )}
          </div>
        ),
      },
      {
        accessorKey: "slug",
        header: t("roles.slug"),
        cell: ({ row }) => (
          <span className="font-mono text-xs text-muted-foreground">
            {row.original.slug}
          </span>
        ),
      },
      {
        id: "permissions",
        header: t("roles.permissions"),
        cell: ({ row }) =>
          t("roles.permissionsCount", {
            count: row.original.permissions?.length ?? 0,
          }),
      },
      {
        id: "actions",
        header: () => <span className="sr-only">{t("common.actions")}</span>,
        cell: ({ row }) => {
          if (row.original.is_system) {
            return (
              <span className="text-xs text-muted-foreground">
                {t("roles.systemRoleReadOnly")}
              </span>
            )
          }
          if (
            !hasPermission("roles.update") &&
            !hasPermission("roles.delete")
          ) {
            return null
          }
          return (
            <div className="flex justify-end">
              <RoleRowActions role={row.original} permissions={permissions} />
            </div>
          )
        },
      },
    ],
    [t, hasPermission, permissions],
  )
}

const RolesManager = () => {
  const { t } = useTranslation()
  const { hasPermission } = useAuth()

  const { data: rolesData } = useQuery({
    queryKey: ["roles"],
    queryFn: async () =>
      (await RolesService.readRoles({ query: { skip: 0, limit: 100 } })).data,
  })
  const { data: permissionsData } = useQuery({
    queryKey: ["permissions"],
    queryFn: async () => (await RolesService.readPermissions()).data,
  })

  const roles = rolesData?.data ?? []
  const permissions = permissionsData ?? []
  const columns = useRoleColumns(permissions)

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-headline-small text-on-surface">
            {t("roles.title")}
          </h1>
          <p className="text-body-medium text-on-surface-variant">
            {t("roles.subtitle")}
          </p>
        </div>
        {hasPermission("roles.create") && permissions.length > 0 && (
          <RoleForm permissions={permissions} />
        )}
      </div>
      <DataTable columns={columns} data={roles} />
    </div>
  )
}

export default RolesManager
