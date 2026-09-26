import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import type { RowSelectionState } from "@tanstack/react-table"
import { Suspense, useState } from "react"
import { useTranslation } from "react-i18next"

import { type UserPublic, UsersService } from "@/client"
import AddUser from "@/components/Admin/AddUser"
import BulkDeleteUsers from "@/components/Admin/BulkDeleteUsers"
import { type UserTableData, useUserColumns } from "@/components/Admin/columns"
import { DataTable } from "@/components/Common/DataTable"
import PendingUsers from "@/components/Pending/PendingUsers"
import useAuth from "@/hooks/useAuth"
import i18n from "@/i18n"

function getUsersQueryOptions() {
  return {
    queryFn: async () =>
      (await UsersService.readUsers({ query: { skip: 0, limit: 100 } })).data,
    queryKey: ["users"],
  }
}

export const Route = createFileRoute("/_layout/admin")({
  component: Admin,
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    const canReadUsers = user.permissions?.includes("users.read") ?? false
    if (!canReadUsers) {
      throw redirect({
        to: "/",
      })
    }
  },
  head: () => ({
    meta: [
      {
        title: i18n.t("meta.admin"),
      },
    ],
  }),
})

function UsersTableContent() {
  const { user: currentUser, hasPermission } = useAuth()
  const { data: users } = useSuspenseQuery(getUsersQueryOptions())
  const canDelete = hasPermission("users.delete")
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})
  const columns = useUserColumns({ withSelection: canDelete })

  const tableData: UserTableData[] = users.data.map((user: UserPublic) => ({
    ...user,
    isCurrentUser: currentUser?.id === user.id,
  }))

  const selectedIds = Object.keys(rowSelection)

  return (
    <div className="flex flex-col gap-4">
      {canDelete && selectedIds.length > 0 && (
        <BulkDeleteUsers
          selectedIds={selectedIds}
          onClearSelection={() => setRowSelection({})}
        />
      )}
      <DataTable
        columns={columns}
        data={tableData}
        enableRowSelection={canDelete}
        isRowSelectable={(user) => !user.isCurrentUser}
        getRowId={(user) => user.id}
        rowSelection={rowSelection}
        onRowSelectionChange={setRowSelection}
      />
    </div>
  )
}

function UsersTable() {
  return (
    <Suspense fallback={<PendingUsers />}>
      <UsersTableContent />
    </Suspense>
  )
}

function Admin() {
  const { t } = useTranslation()
  const { hasPermission } = useAuth()

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {t("admin.title")}
          </h1>
          <p className="text-muted-foreground">{t("admin.subtitle")}</p>
        </div>
        {hasPermission("users.create") && <AddUser />}
      </div>
      <UsersTable />
    </div>
  )
}
