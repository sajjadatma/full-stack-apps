import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Trash2 } from "lucide-react"
import { useState } from "react"
import { Trans, useTranslation } from "react-i18next"

import { UsersService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"

interface BulkDeleteUsersProps {
  selectedIds: string[]
  onClearSelection: () => void
}

interface BulkDeleteResult {
  deleted: number
  failed: number
}

const BulkDeleteUsers = ({
  selectedIds,
  onClearSelection,
}: BulkDeleteUsersProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { t } = useTranslation()

  const mutation = useMutation({
    mutationFn: async (ids: string[]): Promise<BulkDeleteResult> => {
      let deleted = 0
      let failed = 0
      // Delete sequentially so every request goes through the same backend
      // authorization and last-superuser protections as a single delete.
      for (const id of ids) {
        try {
          await UsersService.deleteUser({ path: { user_id: id } })
          deleted += 1
        } catch {
          failed += 1
        }
      }
      return { deleted, failed }
    },
    onSuccess: ({ deleted, failed }) => {
      if (failed === 0) {
        showSuccessToast(t("admin.bulkDeletedSuccess", { count: deleted }))
      } else {
        showErrorToast(t("admin.bulkDeletePartial", { deleted, failed }))
      }
      setIsOpen(false)
      onClearSelection()
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
      queryClient.invalidateQueries({ queryKey: ["currentUser"] })
    },
  })

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border bg-muted/40 px-3 py-2">
        <span
          className="text-sm text-muted-foreground"
          data-testid="selected-users-count"
        >
          {t("admin.selectedCount", { count: selectedIds.length })}
        </span>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={onClearSelection}>
            {t("admin.clearSelection")}
          </Button>
          <Button
            variant="destructive"
            size="sm"
            data-testid="delete-selected-users"
            onClick={() => setIsOpen(true)}
          >
            <Trash2 />
            {t("admin.deleteSelected")}
          </Button>
        </div>
      </div>
      <DialogContent className="sm:max-w-md">
        <form
          onSubmit={(event) => {
            event.preventDefault()
            mutation.mutate(selectedIds)
          }}
        >
          <DialogHeader>
            <DialogTitle>{t("admin.deleteSelected")}</DialogTitle>
            <DialogDescription>
              <Trans
                i18nKey="admin.deleteSelectedDescription"
                values={{ count: selectedIds.length }}
                components={{ strong: <strong /> }}
              />
            </DialogDescription>
          </DialogHeader>

          <DialogFooter className="mt-4">
            <DialogClose asChild>
              <Button variant="outline" disabled={mutation.isPending}>
                {t("common.cancel")}
              </Button>
            </DialogClose>
            <LoadingButton
              variant="destructive"
              type="submit"
              loading={mutation.isPending}
              data-testid="confirm-delete-selected-users"
            >
              {t("common.delete")}
            </LoadingButton>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default BulkDeleteUsers
