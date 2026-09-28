import { Link } from "@tanstack/react-router"
import { useTranslation } from "react-i18next"

import {
  type GenerationJobPublic,
  GenerationsService,
  VisualizationProjectsService,
} from "@/client"
import { AuthenticatedImage } from "@/components/Visualizer/AuthenticatedImage"

export function GenerationHistoryCard({ job }: { job: GenerationJobPublic }) {
  const { t, i18n } = useTranslation()
  const statusLabel =
    job.status === "COMPLETED"
      ? t("generations.status.COMPLETED")
      : job.status === "FAILED"
        ? t("generations.status.FAILED")
        : job.status === "PROCESSING"
          ? t("generations.status.PROCESSING")
          : t("generations.status.PENDING")
  return (
    <article className="grid gap-4 rounded-xl border border-outline-variant bg-surface-container-low p-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(12rem,1fr)] md:items-center">
      <Link
        to="/generations/$jobId"
        params={{ jobId: job.id }}
        className="flex flex-col gap-2 font-medium text-on-surface"
      >
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
          className="h-40 w-full rounded-lg object-cover"
          fallbackLabel={t("visualizer.review.roomFallback")}
        />
        <span>{job.selected_product?.name ?? t("common.na")}</span>
      </Link>
      <div className="flex flex-col gap-2">
        {job.status === "COMPLETED" ? (
          <AuthenticatedImage
            queryKey={["generation-result", job.id]}
            queryFn={async () =>
              (
                await GenerationsService.readGenerationResult({
                  path: { job_id: job.id },
                })
              ).data as Blob
            }
            alt={t("visualizer.result.afterAlt")}
            className="h-40 w-full rounded-lg object-cover"
            fallbackLabel={t("generations.imageUnavailable")}
          />
        ) : (
          <div className="grid h-40 place-items-center rounded-lg bg-surface-container-high text-on-surface-variant">
            {t("generations.noOutput")}
          </div>
        )}
        <span className="text-body-small text-on-surface-variant">
          {job.target_surface === "WALL"
            ? t("visualizer.surface.options.WALL")
            : t("visualizer.surface.options.FLOOR")}
        </span>
      </div>
      <div className="flex flex-col gap-2 text-body-medium">
        <div className="flex items-center gap-3">
          {job.selected_product?.primary_image_id ? (
            <AuthenticatedImage
              queryKey={["generation-product-image", job.id]}
              queryFn={async () =>
                (
                  await GenerationsService.readGenerationProductImage({
                    path: { job_id: job.id },
                  })
                ).data as Blob
              }
              alt={job.selected_product.name}
              className="size-12 rounded-md object-cover"
              fallbackLabel={t("generations.imageUnavailable")}
            />
          ) : null}
          <span>{job.selected_product?.name ?? t("common.na")}</span>
        </div>
        <span className="rounded-full bg-secondary-container px-3 py-1 text-center text-on-secondary-container">
          {statusLabel}
        </span>
        <time dateTime={job.created_at ?? undefined}>
          {new Intl.DateTimeFormat(i18n.resolvedLanguage, {
            dateStyle: "medium",
            timeStyle: "short",
          }).format(new Date(job.created_at ?? Date.now()))}
        </time>
        <span className="text-on-surface-variant">
          {job.selected_product?.sku ?? ""}
        </span>
        {job.selected_product &&
          job.selected_product.width_mm != null &&
          job.selected_product.height_mm != null && (
            <span className="text-body-small text-on-surface-variant">
              {job.selected_product.width_mm} × {job.selected_product.height_mm}{" "}
              mm
              {job.selected_product.material
                ? ` · ${job.selected_product.material}`
                : ""}
              {job.selected_product.finish
                ? ` · ${job.selected_product.finish}`
                : ""}
            </span>
          )}
      </div>
    </article>
  )
}
