import { createFileRoute, redirect } from "@tanstack/react-router"

import { UsersService } from "@/client"
import RolesManager from "@/components/Admin/RolesManager"
import i18n from "@/i18n"

export const Route = createFileRoute("/_layout/roles")({
  component: RolesManager,
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    const canReadRoles = user.permissions?.includes("roles.read") ?? false
    if (!canReadRoles) {
      throw redirect({
        to: "/",
      })
    }
  },
  head: () => ({
    meta: [
      {
        title: i18n.t("meta.roles"),
      },
    ],
  }),
})
