import { Grid2x2, SquareStack } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import { isSurface, type VisualizerSurface } from "./flow"

const surfaces: { value: VisualizerSurface; icon: typeof Grid2x2 }[] = [
  { value: "FLOOR", icon: Grid2x2 },
  { value: "WALL", icon: SquareStack },
]

export function SurfaceStep({
  surface,
  onSelect,
  onBack,
  onNext,
}: {
  surface?: string
  onSelect: (surface: VisualizerSurface) => void
  onBack: () => void
  onNext: () => void
}) {
  const { t } = useTranslation()
  const selected = isSurface(surface) ? surface : undefined

  return (
    <section
      className="flex flex-col gap-4"
      aria-labelledby="visualizer-surface-heading"
      data-testid="visualizer-step-surface"
    >
      <div>
        <h2
          id="visualizer-surface-heading"
          className="text-title-large text-on-surface"
        >
          {t("visualizer.surface.title")}
        </h2>
        <p className="mt-1 text-body-medium text-on-surface-variant">
          {t("visualizer.surface.description")}
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {surfaces.map(({ value, icon: Icon }) => {
          const isSelected = selected === value
          return (
            <button
              key={value}
              type="button"
              aria-pressed={isSelected}
              data-testid={`surface-${value.toLowerCase()}`}
              onClick={() => onSelect(value)}
              className={`flex flex-col items-start gap-3 rounded-xl border p-5 text-start transition-colors ${
                isSelected
                  ? "border-primary bg-primary-container text-on-primary-container"
                  : "border-outline-variant bg-surface-container-low hover:border-primary"
              }`}
            >
              <span className="rounded-full bg-surface-container-high p-3 text-on-surface-variant">
                <Icon className="size-6" aria-hidden="true" />
              </span>
              <span className="text-title-medium">
                {t(`visualizer.surface.options.${value}`)}
              </span>
              <span className="text-body-medium text-on-surface-variant">
                {t(`visualizer.surface.descriptions.${value}`)}
              </span>
            </button>
          )
        })}
      </div>

      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="outline" onClick={onBack}>
          {t("common.goBack")}
        </Button>
        <Button
          type="button"
          disabled={!selected}
          data-testid="surface-next"
          onClick={onNext}
        >
          {t("common.continue")}
        </Button>
      </div>
    </section>
  )
}
