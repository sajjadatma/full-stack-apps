import { EllipsisVertical } from "lucide-react"
import { useState } from "react"

import type { ItemPublic } from "@/client"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import useAuth from "@/hooks/useAuth"
import DeleteItem from "../Items/DeleteItem"
import EditItem from "../Items/EditItem"

interface ItemActionsMenuProps {
  item: ItemPublic
}

export const ItemActionsMenu = ({ item }: ItemActionsMenuProps) => {
  const [open, setOpen] = useState(false)
  const { user, hasPermission } = useAuth()

  const isOwner = item.owner_id === user?.id
  const canUpdate =
    hasPermission("items.update_any") ||
    (hasPermission("items.update_own") && isOwner)
  const canDelete =
    hasPermission("items.delete_any") ||
    (hasPermission("items.delete_own") && isOwner)

  if (!canUpdate && !canDelete) {
    return null
  }

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <EllipsisVertical />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {canUpdate && <EditItem item={item} onSuccess={() => setOpen(false)} />}
        {canDelete && (
          <DeleteItem id={item.id} onSuccess={() => setOpen(false)} />
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
