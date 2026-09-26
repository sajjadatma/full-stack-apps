import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full text-label-large transition-[background-color,box-shadow,color] duration-200 ease-out disabled:pointer-events-none disabled:opacity-40 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:ring-2 focus-visible:ring-ring/60 focus-visible:ring-offset-2 focus-visible:ring-offset-background aria-invalid:ring-destructive/20 aria-invalid:border-destructive",
  {
    variants: {
      variant: {
        // Filled
        default: "bg-primary text-on-primary hover:bg-primary/90 shadow-none",
        // Filled error
        destructive:
          "bg-error text-on-error hover:bg-error/90 focus-visible:ring-error/60",
        // Outlined
        outline:
          "border border-outline text-primary bg-transparent hover:bg-primary/8 aria-expanded:bg-primary/12",
        // Tonal
        secondary:
          "bg-secondary-container text-on-secondary-container hover:bg-secondary-container/85",
        // Elevated
        elevated:
          "bg-surface-container-low text-primary shadow-elevation-1 hover:shadow-elevation-2 hover:bg-primary/8",
        // Text
        ghost: "text-primary bg-transparent hover:bg-primary/8",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-6 py-2 has-[>svg]:px-4",
        sm: "h-9 rounded-full gap-1.5 px-4 text-body-medium has-[>svg]:px-3",
        lg: "h-12 rounded-full px-8 has-[>svg]:px-6",
        icon: "size-10",
        "icon-sm": "size-8",
        "icon-lg": "size-12",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
)

function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot : "button"

  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
