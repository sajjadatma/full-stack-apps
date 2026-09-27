import { useQuery } from "@tanstack/react-query"
import { useTranslation } from "react-i18next"

import { ProductsService, VisualizationProjectsService } from "@/client"
import { ProductImageThumbnail } from "@/components/Products/ProductImageThumbnail"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import { AuthenticatedImage } from "./AuthenticatedImage"
import type { VisualizerSurface } from "./flow"

export function ReviewStep({
  projectId,
  surface,
  productId,
  onBack,
  onGenerate,
  isGenerating,
}: {
  projectId: string
  surface: VisualizerSurface
  productId: string
  onBack: () => void
  onGenerate: () => void
  isGenerating: boolean
}) {
  const { t } = useTranslation()

  const projectQuery = useQuery({
    queryKey: ["visualization-project", projectId],
    queryFn: async () =>
      (
        await VisualizationProjectsService.projectsReadVisualizationProject({
          path: { project_id: projectId },
        })
      ).data,
  })
  const productQuery = useQuery({
    queryKey: ["product-detail", productId],
    queryFn: async () =>
      (await ProductsService.readProduct({ path: { product_id: productId } }))
        .data,
  })

  const product = productQuery.data
  const size = [product?.width_mm, product?.height_mm, product?.thickness_mm]
    .filter((value) => value != null)
    .join(" × ")
  const finish = product?.finish
    ? t(`products.finishes.${product.finish}`, { defaultValue: product.finish })
    : t("common.na")
  const color = product?.color_family
    ? t(`products.colors.${product.color_family}`, {
        defaultValue: product.color_family,
      })
    : t("common.na")

  return (
    <section
      className="flex flex-col gap-4"
      aria-labelledby="visualizer-review-heading"
      data-testid="visualizer-step-review"
    >
      <div>
        <h2
          id="visualizer-review-heading"
          className="text-title-large text-on-surface"
        >
          {t("visualizer.review.title")}
        </h2>
        <p className="mt-1 text-body-medium text-on-surface-variant">
          {t("visualizer.review.description")}
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="flex flex-col gap-2 rounded-xl border border-outline-variant bg-surface-container-low p-4">
          <h3 className="text-title-medium text-on-surface">
            {t("visualizer.review.room")}
          </h3>
          <AuthenticatedImage
            queryKey={["visualization-source-image", projectId]}
            queryFn={async () =>
              (
                await VisualizationProjectsService.projectsReadVisualizationSourceImage(
                  { path: { project_id: projectId } },
                )
              ).data as Blob
            }
            alt={t("visualizer.review.roomAlt")}
            className="max-h-80 w-full rounded-lg object-contain"
            fallbackLabel={t("visualizer.review.roomFallback")}
          />
          {projectQuery.data?.name && (
            <p className="text-body-small text-on-surface-variant">
              {projectQuery.data.name}
            </p>
          )}
          <p className="text-body-medium text-on-surface">
            {t("visualizer.review.surfaceLabel")}:{" "}
            <span className="font-medium">
              {t(`visualizer.surface.options.${surface}`)}
            </span>
          </p>
        </div>

        <div className="flex flex-col gap-3 rounded-xl border border-outline-variant bg-surface-container-low p-4">
          <h3 className="text-title-medium text-on-surface">
            {t("visualizer.review.product")}
          </h3>
          {product ? (
            <>
              <ProductImageThumbnail
                image={product.images?.find((image) => image.is_primary)}
                alt={product.name}
                fallbackLabel={t("products.imagePlaceholder")}
                className="h-40 w-full"
              />
              <div>
                <p className="text-title-medium text-on-surface">
                  {product.name}
                </p>
                <p className="font-mono text-label-small text-on-surface-variant">
                  {product.sku}
                </p>
              </div>
              <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-body-medium text-on-surface-variant">
                <dt>{t("products.size")}</dt>
                <dd dir="ltr">{size || t("common.na")}</dd>
                <dt>{t("products.finish")}</dt>
                <dd>{finish}</dd>
                <dt>{t("visualizer.product.color")}</dt>
                <dd>{color}</dd>
              </dl>
            </>
          ) : (
            <div className="grid h-40 place-items-center text-on-surface-variant">
              {t("products.loading")}
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          disabled={isGenerating}
          onClick={onBack}
        >
          {t("common.goBack")}
        </Button>
        <LoadingButton
          type="button"
          loading={isGenerating}
          data-testid="generate-button"
          onClick={onGenerate}
        >
          {t("visualizer.review.generate")}
        </LoadingButton>
      </div>
    </section>
  )
}
