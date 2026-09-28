import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"

import { UsersService } from "@/client"

export const Route = createFileRoute("/_layout/generations")({
  component: () => <Outlet />,
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    if (!user.permissions?.includes("generations.read_own")) {
      throw redirect({ to: "/" })
    }
  },
})
