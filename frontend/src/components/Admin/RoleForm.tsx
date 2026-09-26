import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import type { TFunction } from "i18next"
import { Pencil, Plus } from "lucide-react"
import { useMemo, useState } from "react"
import { useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod"

import { type PermissionPublic, type RolePublic, RolesService } from "@/client"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { DropdownMenuItem } from "@/components/ui/dropdown-menu"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const createFormSchema = (t: TFunction) =>
  z.object({
    name: z.string().min(1, { message: t("validation.roleNameRequired") }),
    description: z.string().optional(),
  })

type FormData = z.infer<ReturnType<typeof createFormSchema>>

interface RoleFormProps {
  permissions: PermissionPublic[]
  role?: RolePublic
}

const RoleForm = ({ permissions, role }: RoleFormProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const [selected, setSelected] = useState<string[]>(
    role?.permissions?.map((permission) => permission.code) ?? [],
  )
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { t } = useTranslation()
  const formSchema = useMemo(() => createFormSchema(t), [t])

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    defaultValues: {
      name: role?.name ?? "",
      description: role?.description ?? "",
    },
  })

  const groups = useMemo(() => {
    const grouped = new Map<string, PermissionPublic[]>()
    for (const permission of permissions) {
      const group = permission.code.split(".")[0]
      const existing = grouped.get(group) ?? []
      existing.push(permission)
      grouped.set(group, existing)
    }
    return [...grouped.entries()]
  }, [permissions])

  const togglePermission = (code: string) => {
    setSelected((current) =>
      current.includes(code)
        ? current.filter((item) => item !== code)
        : [...current, code],
    )
  }

  const mutation = useMutation({
    mutationFn: async (data: FormData) => {
      if (role) {
        await RolesService.updateRole({
          path: { role_id: role.id },
          body: {
            name: data.name,
            description: data.description ?? null,
            permissions: selected,
          },
        })
      } else {
        await RolesService.createRole({
          body: {
            name: data.name,
            description: data.description ?? null,
            permissions: selected,
          },
        })
      }
    },
    onSuccess: () => {
      showSuccessToast(
        role ? t("roles.updatedSuccess") : t("roles.createdSuccess"),
      )
      setIsOpen(false)
      if (!role) {
        form.reset()
        setSelected([])
      }
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["roles"] })
      queryClient.invalidateQueries({ queryKey: ["currentUser"] })
    },
  })

  const onSubmit = (data: FormData) => mutation.mutate(data)

  const trigger = role ? (
    <DropdownMenuItem
      onSelect={(e) => e.preventDefault()}
      onClick={() => setIsOpen(true)}
    >
      <Pencil />
      {t("roles.editRole")}
    </DropdownMenuItem>
  ) : (
    <DialogTrigger asChild>
      <Button className="my-4">
        <Plus className="me-2" />
        {t("roles.addRole")}
      </Button>
    </DialogTrigger>
  )

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        setIsOpen(open)
        if (open) {
          form.reset({
            name: role?.name ?? "",
            description: role?.description ?? "",
          })
          setSelected(
            role?.permissions?.map((permission) => permission.code) ?? [],
          )
        }
      }}
    >
      {trigger}
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {role ? t("roles.editRole") : t("roles.addRole")}
          </DialogTitle>
          <DialogDescription>
            {role
              ? t("roles.editRoleDescription")
              : t("roles.addRoleDescription")}
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <div className="grid gap-4 py-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      {t("roles.name")}{" "}
                      <span className="text-destructive">*</span>
                    </FormLabel>
                    <FormControl>
                      <Input {...field} required />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("roles.description")}</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid gap-3">
                <FormLabel>{t("roles.permissions")}</FormLabel>
                <div className="grid max-h-64 gap-4 overflow-y-auto rounded-md border p-3">
                  {groups.map(([group, groupPermissions]) => (
                    <div key={group} className="grid gap-2">
                      <p className="text-xs font-semibold uppercase text-muted-foreground">
                        {t(`permissionGroups.${group}`, {
                          defaultValue: group,
                        })}
                      </p>
                      {groupPermissions.map((permission) => (
                        <label
                          key={permission.code}
                          htmlFor={permission.code}
                          className="flex items-center gap-2 text-sm"
                        >
                          <Checkbox
                            id={permission.code}
                            checked={selected.includes(permission.code)}
                            onCheckedChange={() =>
                              togglePermission(permission.code)
                            }
                          />
                          <span>
                            {t(`permissions.${permission.code}`, {
                              defaultValue:
                                permission.description ?? permission.code,
                            })}
                          </span>
                        </label>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline" disabled={mutation.isPending}>
                  {t("common.cancel")}
                </Button>
              </DialogClose>
              <LoadingButton type="submit" loading={mutation.isPending}>
                {t("common.save")}
              </LoadingButton>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

export default RoleForm
