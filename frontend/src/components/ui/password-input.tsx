import * as React from "react"
import { Eye, EyeOff } from "lucide-react"
import { useTranslation } from "react-i18next"

import { cn } from "@/lib/utils"
import { Button } from "./button"

interface PasswordInputProps extends React.ComponentProps<"input"> {
  error?: string
}

const PasswordInput = React.forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ className, error, ...props }, ref) => {
    const [showPassword, setShowPassword] = React.useState(false)
    const { t } = useTranslation()

    return (
      <div className="relative">
        <input
          type={showPassword ? "text" : "password"}
          data-slot="input"
          className={cn(
            "placeholder:text-on-surface-variant selection:bg-primary selection:text-on-primary h-11 w-full min-w-0 rounded-xs border border-outline bg-transparent px-4 py-2 pe-11 text-base transition-[color,box-shadow,border-color] outline-none disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-40",
            "hover:border-on-surface focus-visible:border-primary focus-visible:ring-[3px] focus-visible:ring-primary/25",
            "aria-invalid:border-destructive aria-invalid:ring-destructive/20",
            className,
          )}
          ref={ref}
          aria-invalid={!!error}
          {...props}
        />
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          data-testid="password-toggle"
          className="absolute end-1 top-1/2 -translate-y-1/2 text-on-surface-variant"
          onClick={() => setShowPassword(!showPassword)}
          aria-label={
            showPassword ? t("common.hidePassword") : t("common.showPassword")
          }
        >
          {showPassword ? (
            <EyeOff className="h-4 w-4" />
          ) : (
            <Eye className="h-4 w-4" />
          )}
        </Button>
      </div>
    )
  },
)

PasswordInput.displayName = "PasswordInput"

export { PasswordInput }
