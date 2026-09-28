import { LoaderCircle } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import { GenerationResultView } from "./GenerationResultView"
import { useGenerationJob } from "./useGenerationJob"

export function ResultStep({
  jobId,
  onRetry,
  isRetrying,
  onStartNew,
}: {
  jobId: string
  onRetry: () => void
  isRetrying: boolean
  onStartNew: () => void
}) {
  const { t } = useTranslation()
  const jobQuery = useGenerationJob(jobId)

  if (!jobQuery.data) {
    return (
      <section
        className="grid min-h-48 place-items-center"
        data-testid="visualizer-step-result"
        role="status"
      >
        <LoaderCircle className="size-8 animate-spin text-primary" />
      </section>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <GenerationResultView
        job={jobQuery.data}
        canRetry={jobQuery.data.status === "FAILED"}
        onRetry={onRetry}
        isRetrying={isRetrying}
      />
      {jobQuery.data.status === "FAILED" ? (
        <Button type="button" variant="outline" onClick={onStartNew}>
          {t("visualizer.result.startNew")}
        </Button>
      ) : jobQuery.data.status === "COMPLETED" ? (
        <Button
          type="button"
          data-testid="start-new-visualization"
          onClick={onStartNew}
        >
          {t("visualizer.result.startNew")}
        </Button>
      ) : null}
    </div>
  )
}
