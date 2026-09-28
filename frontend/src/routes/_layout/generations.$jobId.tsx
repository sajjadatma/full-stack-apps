import { useMutation, useQuery } from "@tanstack/react-query"
import {
  createFileRoute,
  Link,
  notFound,
  useNavigate,
} from "@tanstack/react-router"
import { LoaderCircle } from "lucide-react"
import { useTranslation } from "react-i18next"

import { GenerationsService } from "@/client"
import { Button } from "@/components/ui/button"
import { GenerationResultView } from "@/components/Visualizer/GenerationResultView"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import i18n from "@/i18n"
import { handleError } from "@/utils"

export const Route = createFileRoute("/_layout/generations/$jobId")({
  params: {
    parse: (params) => {
      if (
        !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
          params.jobId,
        )
      ) {
        throw notFound()
      }
      return params
    },
  },
  component: GenerationHistoryDetailPage,
  head: () => ({ meta: [{ title: i18n.t("meta.generationDetail") }] }),
})

function GenerationHistoryDetailPage() {
  const { jobId } = Route.useParams()
  const { t, i18n: locale } = useTranslation()
  const navigate = useNavigate()
  const { hasPermission } = useAuth()
  const { showErrorToast } = useCustomToast()
  const canRetry =
    hasPermission("generations.read_own") && hasPermission("generations.create")
  const query = useQuery({
    queryKey: ["generation", jobId],
    queryFn: async () =>
      (await GenerationsService.readGeneration({ path: { job_id: jobId } }))
        .data,
    retry: false,
  })
  const retryMutation = useMutation({
    mutationFn: async () =>
      (await GenerationsService.retryGeneration({ path: { job_id: jobId } }))
        .data,
    onSuccess: (job) =>
      void navigate({ to: "/generations/$jobId", params: { jobId: job.id } }),
    onError: handleError.bind(showErrorToast),
  })

  if (query.isPending)
    return (
      <div className="grid min-h-64 place-items-center" role="status">
        <LoaderCircle className="size-8 animate-spin text-primary" />
        <span className="sr-only">{t("generations.loading")}</span>
      </div>
    )
  if (query.isError)
    return (
      <section className="grid gap-4" role="alert">
        <h1 className="text-headline-small">
          {t("generations.detailErrorTitle")}
        </h1>
        <p>{t("generations.detailErrorDescription")}</p>
        <Button asChild variant="outline">
          <Link to="/generations">{t("generations.backToHistory")}</Link>
        </Button>
      </section>
    )

  const job = query.data
  const statusLabel =
    job.status === "COMPLETED"
      ? t("generations.status.COMPLETED")
      : job.status === "FAILED"
        ? t("generations.status.FAILED")
        : job.status === "PROCESSING"
          ? t("generations.status.PROCESSING")
          : t("generations.status.PENDING")
  return (
    <section
      className="flex flex-col gap-5"
      data-testid="generation-detail-page"
    >
      <Button asChild variant="outline" className="self-start">
        <Link to="/generations">{t("generations.backToHistory")}</Link>
      </Button>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-headline-small text-on-surface">
          {t("generations.detailTitle")}
        </h1>
        <div className="flex items-center gap-3">
          <span className="rounded-full bg-secondary-container px-3 py-1 text-on-secondary-container">
            {statusLabel}
          </span>
          <time dateTime={job.created_at ?? undefined}>
            {new Intl.DateTimeFormat(locale.resolvedLanguage, {
              dateStyle: "medium",
              timeStyle: "short",
            }).format(new Date(job.created_at ?? Date.now()))}
          </time>
        </div>
      </div>
      <GenerationResultView
        job={job}
        canRetry={canRetry && job.status === "FAILED"}
        onRetry={() => retryMutation.mutate()}
        isRetrying={retryMutation.isPending}
      />
    </section>
  )
}
