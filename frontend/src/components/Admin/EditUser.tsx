import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import type { TFunction } from "i18next"
import { Pencil } from "lucide-react"
import { useMemo, useState } from "react"
import { useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod"

import { RolesService, type UserPublic, UsersService } from "@/client"
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
} from "@/components/ui/dialog"
import { DropdownMenuItem } from "@/components/ui/dropdown-menu"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import { PasswordInput } from "@/components/ui/password-input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { roleLabel } from "./roleLabel"

const createFormSchema = (t: TFunction) =>
  z
    .object({
      email: z.email({ message: t("validation.invalidEmail") }),
      full_name: z.string().optional(),
      password: z
        .string()
        .min(8, { message: t("validation.passwordMin") })
        .optional()
        .or(z.literal("")),
      confirm_password: z.string().optional(),
      role_id: z.string().optional(),
      is_active: z.boolean().optional(),
    })
    .refine(
      (data) => !data.password || data.password === data.confirm_password,
      {
        message: t("validation.passwordsDontMatch"),
        path: ["confirm_password"],
      },
    )

type FormData = z.infer<ReturnType<typeof createFormSchema>>

interface EditUserProps {
  user: UserPublic
  onSuccess: () => void
}

const EditUser = ({ user, onSuccess }: EditUserProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { t } = useTranslation()
  const { hasPermission } = useAuth()
  const canAssignRole = hasPermission("roles.assign")
  const formSchema = useMemo(() => createFormSchema(t), [t])

  const { data: rolesData } = useQuery({
    queryKey: ["roles"],
    queryFn: async () =>
      (await RolesService.readRoles({ query: { skip: 0, limit: 100 } })).data,
    enabled: canAssignRole,
  })
  const roles = rolesData?.data ?? []

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      email: user.email,
      full_name: user.full_name ?? undefined,
      role_id: user.role?.id ?? "",
      is_active: user.is_active,
    },
  })

  const mutation = useMutation({
    mutationFn: async (data: FormData) => {
      const { confirm_password: _, role_id, ...submitData } = data
      if (!submitData.password) {
        delete submitData.password
      }
      await UsersService.updateUser({
        path: { user_id: user.id },
        body: submitData,
      })
      if (canAssignRole && role_id && role_id !== user.role?.id) {
        await UsersService.assignUserRole({
          path: { user_id: user.id },
          body: { role_id },
        })
      }
    },
    onSuccess: () => {
      showSuccessToast(t("admin.updatedSuccess"))
      setIsOpen(false)
      onSuccess()
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
      queryClient.invalidateQueries({ queryKey: ["currentUser"] })
    },
  })

  const onSubmit = (data: FormData) => {
    mutation.mutate(data)
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuItem
        onSelect={(e) => e.preventDefault()}
        onClick={() => setIsOpen(true)}
      >
        <Pencil />
        {t("admin.editUser")}
      </DropdownMenuItem>
      <DialogContent className="sm:max-w-md">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <DialogHeader>
              <DialogTitle>{t("admin.editUser")}</DialogTitle>
              <DialogDescription>
                {t("admin.editUserDescription")}
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      {t("common.email")}{" "}
                      <span className="text-destructive">*</span>
                    </FormLabel>
                    <FormControl>
                      <Input
                        placeholder={t("common.email")}
                        type="email"
                        {...field}
                        required
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="full_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("common.fullName")}</FormLabel>
                    <FormControl>
                      <Input
                        placeholder={t("common.fullNameLower")}
                        type="text"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("common.setPassword")}</FormLabel>
                    <FormControl>
                      <PasswordInput
                        placeholder={t("common.password")}
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      {t("admin.passwordOptionalHint")}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="confirm_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("common.confirmPassword")}</FormLabel>
                    <FormControl>
                      <PasswordInput
                        placeholder={t("common.password")}
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {canAssignRole && (
                <FormField
                  control={form.control}
                  name="role_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t("admin.role")}</FormLabel>
                      <Select
                        value={field.value}
                        onValueChange={field.onChange}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder={t("admin.selectRole")} />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {roles.map((role) => (
                            <SelectItem key={role.id} value={role.id}>
                              {roleLabel(role, t)}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}

              <FormField
                control={form.control}
                name="is_active"
                render={({ field }) => (
                  <FormItem className="flex items-center gap-3 space-y-0">
                    <FormControl>
                      <Checkbox
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                    <FormLabel className="font-normal">
                      {t("admin.isActive")}
                    </FormLabel>
                  </FormItem>
                )}
              />
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

export default EditUser
