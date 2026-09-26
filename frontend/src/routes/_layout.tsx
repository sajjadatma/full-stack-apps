import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"
import { LogOut } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Footer } from "@/components/Common/Footer"
import AppSidebar from "@/components/Sidebar/AppSidebar"
import { Button } from "@/components/ui/button"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout")({
  component: Layout,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({
        to: "/login",
      })
    }
  },
})

function Layout() {
  const { logout } = useAuth()
  const { t } = useTranslation()

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="bg-surface">
        <header className="bg-surface/90 supports-[backdrop-filter]:bg-surface/80 sticky top-0 z-10 flex h-16 shrink-0 items-center gap-2 border-b border-outline-variant/50 px-4 backdrop-blur">
          <SidebarTrigger className="-ms-1 text-on-surface-variant" />
          <Button
            variant="ghost"
            className="ms-auto"
            data-testid="logout-button"
            onClick={logout}
          >
            <LogOut aria-hidden="true" />
            {t("navigation.logOut")}
          </Button>
        </header>
        <main className="flex-1 px-4 py-6 md:px-8 md:py-8">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
        <Footer />
      </SidebarInset>
    </SidebarProvider>
  )
}
