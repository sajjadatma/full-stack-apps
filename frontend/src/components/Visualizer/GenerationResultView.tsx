import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, Download, LoaderCircle, RotateCcw } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { GenerationJobPublic } from "@/client"
import { GenerationsService, VisualizationProjectsService } from "@/client"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import { useObjectUrl } from "@/hooks/useObjectUrl"
import { AuthenticatedImage } from "./AuthenticatedImage"

function extensionFor(contentType?: string | null): string {
  if (contentType === "image/jpeg") return "jpg"
  if (contentType === "image/webp") return "webp"
  return "png"
}

export function GenerationResultView({
  job,
  canRetry = false,
  onRetry,
  isRetrying = false,
}: {
  job: GenerationJobPublic
  canRetry?: boolean
  onRetry?: () => void
  isRetrying?: boolean
}) {
  const { t } = useTranslation()
  const resultQuery = useQuery({
    queryKey: ["generation-result", job.id],
    queryFn: async () =>
      (
        await GenerationsService.readGenerationResult({
          path: { job_id: job.id },
        })
      ).data as Blob,
    enabled: job.status === "COMPLETED",
    staleTime: Number.POSITIVE_INFINITY,
    retry: false,
  })
  const resultUrl = useObjectUrl(resultQuery.data)

  if (job.status !== "COMPLETED" && job.status !== "FAILED") {
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
        <GenerationJobSummary job={job} />
      </section>
    )
  }

  if (job.status === "FAILED") {
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
        <GenerationJobSummary job={job} />
        {canRetry && onRetry && (
          <LoadingButton
            type="button"
            loading={isRetrying}
            data-testid="retry-button"
            onClick={onRetry}
          >
            <RotateCcw className="size-4" aria-hidden="true" />
            {t("visualizer.result.retry")}
          </LoadingButton>
        )}
      </section>
    )
  }

  const product = job.selected_product
  const downloadName = `tilevision-${job.id}.${extensionFor(job.output_image_content_type)}`
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
            queryKey={["visualization-source-image", job.project_id]}
            queryFn={async () =>
              (
                await VisualizationProjectsService.projectsReadVisualizationSourceImage(
                  { path: { project_id: job.project_id } },
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
          ) : resultQuery.isError ? (
            <div
              className="grid min-h-48 place-items-center text-on-surface-variant"
              role="img"
              aria-label={t("generations.imageUnavailable")}
            >
              {t("generations.imageUnavailable")}
            </div>
          ) : (
            <div className="grid min-h-48 place-items-center text-on-surface-variant">
              <LoaderCircle className="size-8 animate-spin text-primary" />
            </div>
          )}
        </figure>
      </div>
      <dl className="grid gap-2 rounded-xl border border-outline-variant bg-surface-container-low p-4 text-body-medium sm:grid-cols-2">
        <div className="flex items-center gap-3">
          {product?.primary_image_id ? (
            <AuthenticatedImage
              queryKey={["generation-product-image", job.id]}
              queryFn={async () =>
                (
                  await GenerationsService.readGenerationProductImage({
                    path: { job_id: job.id },
                  })
                ).data as Blob
              }
              alt={product.name}
              className="size-16 shrink-0 rounded-md object-cover"
              fallbackLabel={t("products.imagePlaceholder")}
            />
          ) : (
            <div
              className="size-16 shrink-0 rounded-md bg-surface-container-high"
              role="img"
              aria-label={t("products.imagePlaceholder")}
            />
          )}
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
            {job.target_surface === "WALL"
              ? t("visualizer.surface.options.WALL")
              : t("visualizer.surface.options.FLOOR")}
          </dd>
        </div>
        <div className="flex gap-2">
          <dt className="text-on-surface-variant">SKU</dt>
          <dd className="text-on-surface">{product?.sku ?? t("common.na")}</dd>
        </div>
        <div className="flex gap-2">
          <dt className="text-on-surface-variant">
            {t("generations.dimensions")}
          </dt>
          <dd className="text-on-surface">
            {product?.width_mm != null && product.height_mm != null
              ? `${product.width_mm} × ${product.height_mm}${product.thickness_mm ? ` × ${product.thickness_mm}` : ""} mm`
              : t("common.na")}
          </dd>
        </div>
        <div className="flex gap-2">
          <dt className="text-on-surface-variant">
            {t("generations.productFinish")}
          </dt>
          <dd className="text-on-surface">
            {product?.finish ?? t("common.na")}
          </dd>
        </div>
        <div className="flex gap-2">
          <dt className="text-on-surface-variant">
            {t("generations.productMaterial")}
          </dt>
          <dd className="text-on-surface">
            {product?.material ?? t("common.na")}
          </dd>
        </div>
        <div className="flex gap-2">
          <dt className="text-on-surface-variant">
            {t("generations.productColor")}
          </dt>
          <dd className="text-on-surface">
            {product?.color_family ?? t("common.na")}
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
      </div>
    </section>
  )
}

function GenerationJobSummary({ job }: { job: GenerationJobPublic }) {
  const { t } = useTranslation()
  const product = job.selected_product
  return (
    <dl className="grid w-full gap-3 rounded-xl border border-outline-variant bg-surface-container-low p-4 text-start text-body-medium sm:grid-cols-2">
      <div className="flex items-center gap-3">
        {product?.primary_image_id ? (
          <AuthenticatedImage
            queryKey={["generation-product-image", job.id]}
            queryFn={async () =>
              (
                await GenerationsService.readGenerationProductImage({
                  path: { job_id: job.id },
                })
              ).data as Blob
            }
            alt={product.name}
            className="size-16 shrink-0 rounded-md object-cover"
            fallbackLabel={t("generations.imageUnavailable")}
          />
        ) : null}
        <div>
          <dt className="text-on-surface-variant">
            {t("visualizer.result.productLabel")}
          </dt>
          <dd className="text-on-surface">{product?.name ?? t("common.na")}</dd>
          <dd className="text-on-surface-variant">{product?.sku ?? ""}</dd>
        </div>
      </div>
      <div>
        <dt className="text-on-surface-variant">
          {t("visualizer.result.surfaceLabel")}
        </dt>
        <dd className="text-on-surface">
          {job.target_surface === "WALL"
            ? t("visualizer.surface.options.WALL")
            : t("visualizer.surface.options.FLOOR")}
        </dd>
      </div>
    </dl>
  )
}
