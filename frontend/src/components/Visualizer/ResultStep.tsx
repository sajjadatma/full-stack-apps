import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, Download, LoaderCircle, RotateCcw } from "lucide-react"
import { useTranslation } from "react-i18next"

import {
  GenerationsService,
  ProductsService,
  VisualizationProjectsService,
} from "@/client"
import { ProductImageThumbnail } from "@/components/Products/ProductImageThumbnail"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import { useObjectUrl } from "@/hooks/useObjectUrl"
import { AuthenticatedImage } from "./AuthenticatedImage"
import type { VisualizerSurface } from "./flow"
import { useGenerationJob } from "./useGenerationJob"

function extensionFor(contentType?: string | null): string {
  if (contentType === "image/jpeg") return "jpg"
  if (contentType === "image/webp") return "webp"
  return "png"
}

export function ResultStep({
  projectId,
  productId,
  surface,
  jobId,
  onRetry,
  isRetrying,
  onStartNew,
}: {
  projectId: string
  productId: string
  surface: VisualizerSurface
  jobId: string
  onRetry: () => void
  isRetrying: boolean
  onStartNew: () => void
}) {
  const { t } = useTranslation()
  const jobQuery = useGenerationJob(jobId)
  const job = jobQuery.data

  const resultQuery = useQuery({
    queryKey: ["generation-result", jobId],
    queryFn: async () =>
      (
        await GenerationsService.readGenerationResult({
          path: { job_id: jobId },
        })
      ).data as Blob,
    enabled: job?.status === "COMPLETED",
    staleTime: Number.POSITIVE_INFINITY,
  })
  const resultUrl = useObjectUrl(resultQuery.data)

  const productQuery = useQuery({
    queryKey: ["product-detail", productId],
    queryFn: async () =>
      (await ProductsService.readProduct({ path: { product_id: productId } }))
        .data,
  })
  const product = productQuery.data

  if (job && job.status !== "COMPLETED" && job.status !== "FAILED") {
    return (
      <section
        className="flex min-h-48 flex-col items-center justify-center gap-4 rounded-xl border border-outline-variant bg-surface-container-low p-8 text-center"
        data-testid="visualizer-step-result"
        role="status"
        aria-live="polite"
      >
        <LoaderCircle className="size-10 animate-spin text-primary" />
        <p className="text-title-medium text-on-surface">
          {t("visualizer.generate.processing")}
        </p>
      </section>
    )
  }

  if (job?.status === "FAILED") {
    return (
      <section
        className="flex flex-col gap-4"
        aria-labelledby="visualizer-result-heading"
        data-testid="visualizer-step-result"
      >
        <div className="flex flex-col items-start gap-3 rounded-xl border border-error bg-error-container p-6 text-on-error-container">
          <span className="flex items-center gap-2">
            <AlertTriangle className="size-6" aria-hidden="true" />
            <h2 id="visualizer-result-heading" className="text-title-large">
              {t("visualizer.result.failedTitle")}
            </h2>
          </span>
          <p className="text-body-medium">
            {job.error_message ?? t("visualizer.result.failedFallback")}
          </p>
          {job.error_code && (
            <p className="font-mono text-label-small opacity-80">
              {job.error_code}
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <LoadingButton
            type="button"
            loading={isRetrying}
            data-testid="retry-button"
            onClick={onRetry}
          >
            <RotateCcw className="size-4" aria-hidden="true" />
            {t("visualizer.result.retry")}
          </LoadingButton>
          <Button type="button" variant="outline" onClick={onStartNew}>
            {t("visualizer.result.startNew")}
          </Button>
        </div>
      </section>
    )
  }

  const downloadName = `tilevision-${jobId}.${extensionFor(
    job?.output_image_content_type,
  )}`

  return (
    <section
      className="flex flex-col gap-4"
      aria-labelledby="visualizer-result-heading"
      data-testid="visualizer-step-result"
    >
      <div>
        <h2
          id="visualizer-result-heading"
          className="text-title-large text-on-surface"
        >
          {t("visualizer.result.title")}
        </h2>
        <p className="mt-1 text-body-medium text-on-surface-variant">
          {t("visualizer.result.description")}
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <figure className="flex flex-col gap-2 rounded-xl border border-outline-variant bg-surface-container-low p-4">
          <figcaption className="text-title-medium text-on-surface">
            {t("visualizer.result.before")}
          </figcaption>
          <AuthenticatedImage
            queryKey={["visualization-source-image", projectId]}
            queryFn={async () =>
              (
                await VisualizationProjectsService.projectsReadVisualizationSourceImage(
                  { path: { project_id: projectId } },
                )
              ).data as Blob
            }
            alt={t("visualizer.result.beforeAlt")}
            className="max-h-96 w-full rounded-lg object-contain"
            fallbackLabel={t("visualizer.review.roomFallback")}
          />
        </figure>

        <figure className="flex flex-col gap-2 rounded-xl border border-outline-variant bg-surface-container-low p-4">
          <figcaption className="text-title-medium text-on-surface">
            {t("visualizer.result.after")}
          </figcaption>
          {resultUrl ? (
            <img
              data-testid="generation-result-image"
              src={resultUrl}
              alt={t("visualizer.result.afterAlt")}
              className="max-h-96 w-full rounded-lg object-contain"
            />
          ) : (
            <div className="grid min-h-48 place-items-center text-on-surface-variant">
              <LoaderCircle className="size-8 animate-spin text-primary" />
            </div>
          )}
        </figure>
      </div>

      <dl className="grid gap-2 rounded-xl border border-outline-variant bg-surface-container-low p-4 text-body-medium sm:grid-cols-2">
        <div className="flex items-center gap-3">
          <ProductImageThumbnail
            image={product?.images?.find((image) => image.is_primary)}
            alt={product?.name ?? t("visualizer.result.productLabel")}
            fallbackLabel={t("products.imagePlaceholder")}
            className="size-16 shrink-0"
          />
          <div className="flex flex-col">
            <dt className="text-on-surface-variant">
              {t("visualizer.result.productLabel")}
            </dt>
            <dd className="text-on-surface">
              {product?.name ?? t("common.na")}
            </dd>
          </div>
        </div>
        <div className="flex gap-2">
          <dt className="text-on-surface-variant">
            {t("visualizer.result.surfaceLabel")}
          </dt>
          <dd className="text-on-surface">
            {t(`visualizer.surface.options.${surface}`)}
          </dd>
        </div>
      </dl>

      <div className="flex flex-wrap gap-2">
        <Button asChild variant="outline" disabled={!resultUrl}>
          <a href={resultUrl || undefined} download={downloadName}>
            <Download className="size-4" aria-hidden="true" />
            {t("visualizer.result.download")}
          </a>
        </Button>
        <Button
          type="button"
          data-testid="start-new-visualization"
          onClick={onStartNew}
        >
          {t("visualizer.result.startNew")}
        </Button>
      </div>
    </section>
  )
}
