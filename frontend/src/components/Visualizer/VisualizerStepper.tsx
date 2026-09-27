import { Check } from "lucide-react"
import { useTranslation } from "react-i18next"

import { stepIndex, type VisualizerStep, visualizerSteps } from "./flow"

const labels = {
  upload: "visualizer.steps.upload",
  surface: "visualizer.steps.surface",
  product: "visualizer.steps.product",
  review: "visualizer.steps.review",
  generate: "visualizer.steps.generate",
  result: "visualizer.steps.result",
} as const satisfies Record<VisualizerStep, string>

export function VisualizerStepper({ current }: { current: VisualizerStep }) {
  const { t } = useTranslation()
  const currentIndex = stepIndex[current]

  return (
    <nav
      aria-label={t("visualizer.stepperLabel")}
      data-testid="visualizer-stepper"
    >
      <ol className="hidden items-center gap-2 md:flex">
        {visualizerSteps.map((step, index) => {
          const isComplete = index < currentIndex
          const isCurrent = index === currentIndex
          return (
            <li key={step} className="flex flex-1 items-center gap-2">
              <div
                className={`flex size-8 shrink-0 items-center justify-center rounded-full text-label-large ${
                  isCurrent
                    ? "bg-primary text-on-primary"
                    : isComplete
                      ? "bg-secondary-container text-on-secondary-container"
                      : "bg-surface-container-high text-on-surface-variant"
                }`}
                aria-current={isCurrent ? "step" : undefined}
              >
                {isComplete ? (
                  <Check className="size-4" aria-hidden="true" />
                ) : (
                  <span>{index + 1}</span>
                )}
              </div>
              <span
                className={`text-label-large ${
                  isCurrent ? "text-on-surface" : "text-on-surface-variant"
                }`}
              >
                {t(labels[step])}
              </span>
              {index < visualizerSteps.length - 1 && (
                <span
                  className={`mx-1 hidden h-px flex-1 lg:block ${
                    isComplete ? "bg-primary" : "bg-outline-variant"
                  }`}
                  aria-hidden="true"
                />
              )}
            </li>
          )
        })}
      </ol>
      <p className="text-label-large text-on-surface-variant md:hidden">
        {t("visualizer.stepProgress", {
          current: currentIndex + 1,
          total: visualizerSteps.length,
        })}{" "}
        · {t(labels[current])}
      </p>
    </nav>
  )
}
