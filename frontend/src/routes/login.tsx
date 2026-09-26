import { zodResolver } from "@hookform/resolvers/zod"
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router"
import type { TFunction } from "i18next"
import { useMemo } from "react"
import { useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod"

import type { Body_login_login_access_token as AccessToken } from "@/client"
import { AuthLayout } from "@/components/Common/AuthLayout"
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
import { PasswordInput } from "@/components/ui/password-input"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import i18n from "@/i18n"

const createFormSchema = (t: TFunction) =>
  z.object({
    username: z.email({ message: t("validation.invalidEmail") }),
    password: z
      .string()
      .min(1, { message: t("validation.passwordRequired") })
      .min(8, { message: t("validation.passwordMin") }),
  }) satisfies z.ZodType<AccessToken>

type FormData = z.infer<ReturnType<typeof createFormSchema>>

export const Route = createFileRoute("/login")({
  component: Login,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: "/",
      })
    }
  },
  head: () => ({
    meta: [
      {
        title: i18n.t("meta.login"),
      },
    ],
  }),
})

function Login() {
  const { loginMutation } = useAuth()
  const { t } = useTranslation()
  const formSchema = useMemo(() => createFormSchema(t), [t])
  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      username: "",
      password: "",
    },
  })

  const onSubmit = (data: FormData) => {
    if (loginMutation.isPending) return
    loginMutation.mutate(data)
  }

  return (
    <AuthLayout>
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="flex flex-col gap-6"
        >
          <div className="flex flex-col items-center gap-2 text-center">
            <h1 className="text-2xl font-bold">{t("auth.loginTitle")}</h1>
          </div>

          <div className="grid gap-4">
            <FormField
              control={form.control}
              name="username"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("common.email")}</FormLabel>
                  <FormControl>
                    <Input
                      data-testid="email-input"
                      placeholder="user@example.com"
                      type="email"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage className="text-xs" />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <div className="flex items-center">
                    <FormLabel>{t("common.password")}</FormLabel>
                    <RouterLink
                      to="/recover-password"
                      className="ms-auto text-sm underline-offset-4 hover:underline"
                    >
                      {t("auth.forgotPassword")}
                    </RouterLink>
                  </div>
                  <FormControl>
                    <PasswordInput
                      data-testid="password-input"
                      placeholder={t("common.password")}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage className="text-xs" />
                </FormItem>
              )}
            />

            <LoadingButton type="submit" loading={loginMutation.isPending}>
              {t("auth.loginButton")}
            </LoadingButton>
          </div>

          <div className="text-center text-sm">
            {t("auth.noAccount")}{" "}
            <RouterLink to="/signup" className="underline underline-offset-4">
              {t("auth.signUpLink")}
            </RouterLink>
          </div>
        </form>
      </Form>
    </AuthLayout>
  )
}
