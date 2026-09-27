import { LoaderCircle } from "lucide-react"
import { useEffect } from "react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import { isTerminalStatus, useGenerationJob } from "./useGenerationJob"

export function GenerateStep({
  jobId,
  onFinished,
}: {
  jobId: string
  onFinished: () => void
}) {
  const { t } = useTranslation()
  const query = useGenerationJob(jobId)

  useEffect(() => {
    if (isTerminalStatus(query.data?.status)) {
      onFinished()
    }
  }, [query.data?.status, onFinished])

  return (
    <section
      className="flex flex-col gap-4"
      aria-labelledby="visualizer-generate-heading"
      data-testid="visualizer-step-generate"
    >
      <div>
        <h2
          id="visualizer-generate-heading"
          className="text-title-large text-on-surface"
        >
          {t("visualizer.generate.title")}
        </h2>
        <p className="mt-1 text-body-medium text-on-surface-variant">
          {t("visualizer.generate.description")}
        </p>
      </div>

      {query.isError ? (
        <div className="grid min-h-48 place-items-center" role="alert">
          <div className="flex flex-col items-center gap-3">
            <p className="text-body-large text-on-surface">
              {t("visualizer.generate.loadError")}
            </p>
            <Button variant="outline" onClick={() => void query.refetch()}>
              {t("products.retry")}
            </Button>
          </div>
        </div>
      ) : (
        <div
          className="flex min-h-48 flex-col items-center justify-center gap-4 rounded-xl border border-outline-variant bg-surface-container-low p-8 text-center"
          role="status"
          aria-live="polite"
        >
          <LoaderCircle className="size-10 animate-spin text-primary" />
          <p className="text-title-medium text-on-surface">
            {t(
              query.data?.status === "PROCESSING"
                ? "visualizer.generate.processing"
                : "visualizer.generate.pending",
            )}
          </p>
          <p className="text-body-medium text-on-surface-variant">
            {t("visualizer.generate.keepOpen")}
          </p>
        </div>
      )}
    </section>
  )
}
