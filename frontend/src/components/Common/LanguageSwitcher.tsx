import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Check, Languages } from "lucide-react"
import { useTranslation } from "react-i18next"

import { UsersService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar"
import { isLoggedIn } from "@/hooks/useAuth"
import { type Language, SUPPORTED_LANGUAGES } from "@/i18n"
import { useLanguage } from "@/i18n/useLanguage"

const LANGUAGE_LABEL_KEYS: Record<Language, "common.english" | "common.farsi"> =
  {
    en: "common.english",
    fa: "common.farsi",
  }

function useLanguageSwitcher() {
  const { language, changeLanguage } = useLanguage()
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: (locale: Language) =>
      UsersService.updateUserMe({ body: { locale } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["currentUser"] })
    },
  })

  const handleChange = (locale: Language) => {
    changeLanguage(locale)
    if (isLoggedIn()) {
      mutation.mutate(locale)
    }
  }

  return { language, handleChange }
}

function LanguageItems({
  language,
  onChange,
}: {
  language: Language
  onChange: (locale: Language) => void
}) {
  const { t } = useTranslation()

  return (
    <>
      {SUPPORTED_LANGUAGES.map((locale) => (
        <DropdownMenuItem
          key={locale}
          data-testid={`language-${locale}`}
          onClick={() => onChange(locale)}
        >
          <span className="flex-1">{t(LANGUAGE_LABEL_KEYS[locale])}</span>
          {language === locale && <Check className="size-4" />}
        </DropdownMenuItem>
      ))}
    </>
  )
}

export function LanguageSwitcher() {
  const { t } = useTranslation()
  const { language, handleChange } = useLanguageSwitcher()

  return (
    <DropdownMenu modal={false}>
      <DropdownMenuTrigger asChild>
        <Button
          data-testid="language-button"
          variant="outline"
          size="icon"
          aria-label={t("common.language")}
        >
          <Languages className="h-[1.2rem] w-[1.2rem]" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <LanguageItems language={language} onChange={handleChange} />
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export function SidebarLanguageSwitcher() {
  const { t } = useTranslation()
  const { isMobile } = useSidebar()
  const { language, handleChange } = useLanguageSwitcher()
  const { isRtl } = useLanguage()

  return (
    <SidebarMenuItem>
      <DropdownMenu modal={false}>
        <DropdownMenuTrigger asChild>
          <SidebarMenuButton
            tooltip={t("common.language")}
            data-testid="language-button"
          >
            <Languages className="size-4 text-muted-foreground" />
            <span>{t("common.language")}</span>
          </SidebarMenuButton>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          side={isMobile ? "top" : isRtl ? "left" : "right"}
          align="end"
          className="w-(--radix-dropdown-menu-trigger-width) min-w-56"
        >
          <LanguageItems language={language} onChange={handleChange} />
        </DropdownMenuContent>
      </DropdownMenu>
    </SidebarMenuItem>
  )
}
