import { useQuery } from "@tanstack/react-query"
import { LoaderCircle, Package, Search } from "lucide-react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"

import { type ProductPublic, ProductsService } from "@/client"
import { ProductImageThumbnail } from "@/components/Products/ProductImageThumbnail"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import type { VisualizerSurface } from "./flow"

const PAGE_SIZE = 12

function primaryImage(product: ProductPublic) {
  return product.images?.find((image) => image.is_primary)
}

export function ProductStep({
  surface,
  selectedProductId,
  onSelect,
  onBack,
  onNext,
}: {
  surface: VisualizerSurface
  selectedProductId?: string
  onSelect: (productId: string) => void
  onBack: () => void
  onNext: () => void
}) {
  const { t } = useTranslation()
  const [search, setSearch] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const [page, setPage] = useState(0)

  useEffect(() => {
    const timeout = window.setTimeout(
      () => setDebouncedSearch(search.trim()),
      250,
    )
    return () => window.clearTimeout(timeout)
  }, [search])

  const query = useQuery({
    queryKey: ["visualizer-products", surface, debouncedSearch, page],
    queryFn: async () =>
      (
        await ProductsService.readProducts({
          query: {
            q: debouncedSearch || undefined,
            suitable_surface: surface,
            is_active: true,
            skip: page * PAGE_SIZE,
            limit: PAGE_SIZE,
          },
        })
      ).data,
  })

  const products = query.data?.data ?? []
  const pageCount = Math.max(1, Math.ceil((query.data?.count ?? 0) / PAGE_SIZE))

  return (
    <section
      className="flex flex-col gap-4"
      aria-labelledby="visualizer-product-heading"
      data-testid="visualizer-step-product"
    >
      <div>
        <h2
          id="visualizer-product-heading"
          className="text-title-large text-on-surface"
        >
          {t("visualizer.product.title")}
        </h2>
        <p className="mt-1 text-body-medium text-on-surface-variant">
          {t("visualizer.product.description", {
            surface: t(`visualizer.surface.options.${surface}`),
          })}
        </p>
      </div>

      <div className="relative">
        <Search className="absolute start-3 top-3 size-4 text-on-surface-variant" />
        <Input
          className="ps-10"
          data-testid="product-search"
          aria-label={t("visualizer.product.searchLabel")}
          placeholder={t("visualizer.product.searchPlaceholder")}
          value={search}
          onChange={(event) => {
            setSearch(event.target.value)
            setPage(0)
          }}
        />
      </div>

      {query.isPending ? (
        <div
          className="grid min-h-48 place-items-center text-on-surface-variant"
          role="status"
        >
          <LoaderCircle className="size-8 animate-spin text-primary" />
        </div>
      ) : query.isError ? (
        <div className="grid min-h-48 place-items-center" role="alert">
          <div className="flex flex-col items-center gap-3">
            <p className="text-body-large text-on-surface">
              {t("visualizer.product.loadError")}
            </p>
            <Button variant="outline" onClick={() => void query.refetch()}>
              {t("products.retry")}
            </Button>
          </div>
        </div>
      ) : products.length === 0 ? (
        <div className="grid min-h-48 place-items-center text-center">
          <div className="flex max-w-md flex-col items-center gap-3">
            <span className="rounded-full bg-secondary-container p-4 text-on-secondary-container">
              <Package className="size-8" />
            </span>
            <h3 className="text-title-medium text-on-surface">
              {t("visualizer.product.emptyTitle")}
            </h3>
            <p className="text-body-medium text-on-surface-variant">
              {t("visualizer.product.emptyDescription")}
            </p>
          </div>
        </div>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {products.map((product) => {
            const image = primaryImage(product)
            const selectable = Boolean(image)
            const isSelected = product.id === selectedProductId
            const size = [product.width_mm, product.height_mm]
              .filter((value) => value != null)
              .join(" × ")
            const finish = product.finish
              ? t(`products.finishes.${product.finish}`, {
                  defaultValue: product.finish,
                })
              : t("common.na")
            const color = product.color_family
              ? t(`products.colors.${product.color_family}`, {
                  defaultValue: product.color_family,
                })
              : t("common.na")
            return (
              <li key={product.id}>
                <button
                  type="button"
                  disabled={!selectable}
                  aria-pressed={isSelected}
                  data-testid={`product-option-${product.id}`}
                  onClick={() => selectable && onSelect(product.id)}
                  className={`flex h-full w-full flex-col gap-3 rounded-xl border p-4 text-start transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
                    isSelected
                      ? "border-primary bg-primary-container text-on-primary-container"
                      : "border-outline-variant bg-surface-container-low hover:border-primary"
                  }`}
                >
                  <ProductImageThumbnail
                    image={image}
                    alt={product.name}
                    fallbackLabel={t("products.imagePlaceholder")}
                    className="h-40 w-full"
                  />
                  <div className="flex flex-col gap-1">
                    <span className="text-title-medium text-on-surface">
                      {product.name}
                    </span>
                    <span className="font-mono text-label-small text-on-surface-variant">
                      {product.sku}
                    </span>
                  </div>
                  <dl className="grid grid-cols-[auto_1fr] gap-x-2 text-body-small text-on-surface-variant">
                    <dt>{t("products.size")}</dt>
                    <dd dir="ltr">{size || t("common.na")}</dd>
                    <dt>{t("products.finish")}</dt>
                    <dd>{finish}</dd>
                    <dt>{t("visualizer.product.color")}</dt>
                    <dd>{color}</dd>
                  </dl>
                  {!selectable && (
                    <span className="text-label-medium text-error">
                      {t("visualizer.product.noImage")}
                    </span>
                  )}
                </button>
              </li>
            )
          })}
        </ul>
      )}

      {query.data && query.data.count > PAGE_SIZE && (
        <div className="flex items-center justify-between">
          <span className="text-body-small text-on-surface-variant">
            {t("products.pageSummary", {
              page: page + 1,
              pages: pageCount,
              count: query.data.count,
            })}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 0 || query.isFetching}
              onClick={() => setPage((current) => Math.max(0, current - 1))}
            >
              {t("pagination.previous")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page + 1 >= pageCount || query.isFetching}
              onClick={() => setPage((current) => current + 1)}
            >
              {t("pagination.next")}
            </Button>
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="outline" onClick={onBack}>
          {t("common.goBack")}
        </Button>
        <Button
          type="button"
          disabled={!selectedProductId}
          data-testid="product-next"
          onClick={onNext}
        >
          {t("common.continue")}
        </Button>
      </div>
    </section>
  )
}
