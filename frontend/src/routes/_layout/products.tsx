import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import { LoaderCircle, Package, Search, SlidersHorizontal } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import type { BrandPublic, CategoryPublic, ProductPublic } from "@/client"
import {
  BrandsService,
  CategoriesService,
  ProductsService,
  UsersService,
} from "@/client"
import { ProductFormDialog } from "@/components/Products/ProductFormDialog"
import { ProductImageThumbnail } from "@/components/Products/ProductImageThumbnail"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import i18n from "@/i18n"
import { useLanguage } from "@/i18n/useLanguage"
import { handleError } from "@/utils"

const PAGE_SIZE = 12

type SortKey = "name" | "price" | "stock_quantity"
type Filters = {
  category_id: string
  brand_id: string
  product_type: string
  material: string
  finish: string
  usage_area: string
  color_family: string
  stock_state: "in_stock" | "low_stock" | "out_of_stock" | ""
  is_active: "true" | "false" | ""
  is_featured: "true" | "false" | ""
  min_price: string
  max_price: string
  width_mm: string
  height_mm: string
  thickness_mm: string
}

const initialFilters: Filters = {
  category_id: "",
  brand_id: "",
  product_type: "",
  material: "",
  finish: "",
  usage_area: "",
  color_family: "",
  stock_state: "",
  is_active: "true",
  is_featured: "",
  min_price: "",
  max_price: "",
  width_mm: "",
  height_mm: "",
  thickness_mm: "",
}

export const Route = createFileRoute("/_layout/products")({
  component: ProductsPage,
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    const canRead =
      user.permissions?.includes("products.read") ||
      user.permissions?.includes("products.read_any")
    if (!canRead) throw redirect({ to: "/" })
  },
  head: () => ({ meta: [{ title: i18n.t("meta.products") }] }),
})

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  options: { value: string; label: string }[]
}) {
  const selectId = `product-filter-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`
  return (
    <div className="grid min-w-36 gap-1.5 text-label-medium text-on-surface-variant">
      <label htmlFor={selectId}>{label}</label>
      <Select
        value={value || "all"}
        onValueChange={(next) => onChange(next === "all" ? "" : next)}
      >
        <SelectTrigger
          id={selectId}
          className="h-10 w-full bg-surface text-on-surface"
        >
          <SelectValue placeholder={label} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">{i18n.t("products.allOptions")}</SelectItem>
          {options.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

function ProductsPage() {
  const { t } = useTranslation()
  const { language } = useLanguage()
  const { hasPermission } = useAuth()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const productTypeOptions = [
    { value: "floor_tile", label: t("products.types.floor_tile") },
    { value: "wall_tile", label: t("products.types.wall_tile") },
    { value: "mosaic", label: t("products.types.mosaic") },
    { value: "decorative", label: t("products.types.decorative") },
  ]
  const materialOptions = [
    { value: "ceramic", label: t("products.materials.ceramic") },
    { value: "porcelain", label: t("products.materials.porcelain") },
    { value: "stone", label: t("products.materials.stone") },
    { value: "glass", label: t("products.materials.glass") },
    { value: "other", label: t("products.materials.other") },
  ]
  const finishOptions = [
    { value: "matte", label: t("products.finishes.matte") },
    { value: "glossy", label: t("products.finishes.glossy") },
    { value: "polished", label: t("products.finishes.polished") },
    { value: "satin", label: t("products.finishes.satin") },
    { value: "textured", label: t("products.finishes.textured") },
    { value: "anti_slip", label: t("products.finishes.anti_slip") },
  ]
  const usageAreaOptions = [
    { value: "floor", label: t("products.usageAreas.floor") },
    { value: "wall", label: t("products.usageAreas.wall") },
    { value: "indoor", label: t("products.usageAreas.indoor") },
    { value: "outdoor", label: t("products.usageAreas.outdoor") },
  ]
  const stockStateOptions = [
    { value: "in_stock", label: t("products.stockStates.in_stock") },
    { value: "low_stock", label: t("products.stockStates.low_stock") },
    { value: "out_of_stock", label: t("products.stockStates.out_of_stock") },
  ]
  const colorOptions = [
    { value: "white", label: t("products.colors.white") },
    { value: "grey", label: t("products.colors.grey") },
    { value: "beige", label: t("products.colors.beige") },
    { value: "black", label: t("products.colors.black") },
    { value: "brown", label: t("products.colors.brown") },
    { value: "blue", label: t("products.colors.blue") },
    { value: "green", label: t("products.colors.green") },
    { value: "multi", label: t("products.colors.multi") },
  ]
  const [search, setSearch] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")
  const [filters, setFilters] = useState<Filters>(initialFilters)
  const [page, setPage] = useState(0)
  const [sort, setSort] = useState<{ key: SortKey; direction: "asc" | "desc" }>(
    {
      key: "name",
      direction: "asc",
    },
  )
  const canCreate = hasPermission("products.create")
  const canUpdate = hasPermission("products.update")
  const canManageImages = hasPermission("products.manage_images")
  const canReadAll = hasPermission("products.read_any")

  useEffect(() => {
    const timeout = window.setTimeout(
      () => setDebouncedSearch(search.trim()),
      250,
    )
    return () => window.clearTimeout(timeout)
  }, [search])

  const query = useQuery({
    queryKey: ["products", page, debouncedSearch, filters],
    queryFn: async () =>
      (
        await ProductsService.readProducts({
          query: {
            skip: page * PAGE_SIZE,
            limit: PAGE_SIZE,
            q: debouncedSearch || undefined,
            category_id: filters.category_id || undefined,
            brand_id: filters.brand_id || undefined,
            product_type: filters.product_type || undefined,
            material: filters.material || undefined,
            finish: filters.finish || undefined,
            usage_area: filters.usage_area || undefined,
            color_family: filters.color_family || undefined,
            stock_state: filters.stock_state || undefined,
            is_active:
              filters.is_active === ""
                ? undefined
                : filters.is_active === "true",
            is_featured:
              filters.is_featured === ""
                ? undefined
                : filters.is_featured === "true",
            min_price: filters.min_price || undefined,
            max_price: filters.max_price || undefined,
            width_mm: filters.width_mm ? Number(filters.width_mm) : undefined,
            height_mm: filters.height_mm
              ? Number(filters.height_mm)
              : undefined,
            thickness_mm: filters.thickness_mm
              ? Number(filters.thickness_mm)
              : undefined,
          },
        })
      ).data,
  })
  const categoriesQuery = useQuery({
    queryKey: ["categories", "product-form"],
    queryFn: async () => (await CategoriesService.readCategories()).data,
  })
  const brandsQuery = useQuery({
    queryKey: ["brands", "product-form"],
    queryFn: async () => (await BrandsService.readBrands()).data,
  })
  const deactivateMutation = useMutation({
    mutationFn: (productId: string) =>
      ProductsService.deactivateProduct({ path: { product_id: productId } }),
    onSuccess: () => {
      showSuccessToast(t("products.deactivatedSuccess"))
      void queryClient.invalidateQueries({ queryKey: ["products"] })
    },
    onError: handleError.bind(showErrorToast),
  })

  const updateFilter = <K extends keyof Filters>(key: K, value: Filters[K]) => {
    setFilters((current) => ({ ...current, [key]: value }))
    setPage(0)
  }

  const clearFilters = () => {
    setFilters(initialFilters)
    setSearch("")
    setPage(0)
  }

  const categories = categoriesQuery.data?.data ?? []
  const brands = brandsQuery.data?.data ?? []
  const products = query.data?.data ?? []
  const pageCount = Math.max(1, Math.ceil((query.data?.count ?? 0) / PAGE_SIZE))
  const sortedProducts = useMemo(() => {
    const direction = sort.direction === "asc" ? 1 : -1
    return [...products].sort((left, right) => {
      const a = left[sort.key]
      const b = right[sort.key]
      if (sort.key === "name")
        return String(a).localeCompare(String(b)) * direction
      return (Number(a ?? 0) - Number(b ?? 0)) * direction
    })
  }, [products, sort])

  const changeSort = (key: SortKey) => {
    setSort((current) => ({
      key,
      direction:
        current.key === key && current.direction === "asc" ? "desc" : "asc",
    }))
  }

  const formatPrice = (price?: string | null) =>
    price == null
      ? t("common.na")
      : new Intl.NumberFormat(language, { maximumFractionDigits: 2 }).format(
          Number(price),
        )

  const activeFilterCount = Object.entries(filters).filter(
    ([key, value]) =>
      value !== "" && !(key === "is_active" && value === "true"),
  ).length
  const anyResults = (query.data?.count ?? 0) > 0

  return (
    <div className="flex flex-col gap-6" data-testid="products-page">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-headline-small text-on-surface">
            {t("products.title")}
          </h1>
          <p className="mt-1 text-body-medium text-on-surface-variant">
            {t("products.subtitle")}
          </p>
        </div>
        <ProductFormDialog
          categories={categories}
          brands={brands}
          canCreate={canCreate}
          canUpdate={canUpdate}
          canManageImages={canManageImages}
        />
      </div>

      <section
        className="rounded-xl border border-outline-variant bg-surface-container-low p-4 shadow-elevation-1"
        aria-label={t("products.filters")}
      >
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-title-medium text-on-surface">
            <SlidersHorizontal className="size-4 text-primary" />
            {t("products.filters")}
            {activeFilterCount > 0 && (
              <Badge variant="secondary">{activeFilterCount}</Badge>
            )}
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={clearFilters}
          >
            {t("products.clearFilters")}
          </Button>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="relative grid gap-1.5 text-label-medium text-on-surface-variant sm:col-span-2">
            <label htmlFor="products-search">{t("products.searchLabel")}</label>
            <Search className="absolute start-3 top-10 size-4 text-on-surface-variant" />
            <Input
              id="products-search"
              aria-label={t("products.searchLabel")}
              className="ps-10"
              placeholder={t("products.searchPlaceholder")}
              value={search}
              onChange={(event) => {
                setSearch(event.target.value)
                setPage(0)
              }}
            />
          </div>
          <FilterSelect
            label={t("products.category")}
            value={filters.category_id}
            onChange={(v) => updateFilter("category_id", v)}
            options={categories.map((category) => ({
              value: category.id,
              label: category.name,
            }))}
          />
          <FilterSelect
            label={t("products.brand")}
            value={filters.brand_id}
            onChange={(v) => updateFilter("brand_id", v)}
            options={brands.map((brand) => ({
              value: brand.id,
              label: brand.name,
            }))}
          />
          <FilterSelect
            label={t("products.productType")}
            value={filters.product_type}
            onChange={(v) => updateFilter("product_type", v)}
            options={productTypeOptions}
          />
          <FilterSelect
            label={t("products.material")}
            value={filters.material}
            onChange={(v) => updateFilter("material", v)}
            options={materialOptions}
          />
          <FilterSelect
            label={t("products.finish")}
            value={filters.finish}
            onChange={(v) => updateFilter("finish", v)}
            options={finishOptions}
          />
          <FilterSelect
            label={t("products.usageArea")}
            value={filters.usage_area}
            onChange={(v) => updateFilter("usage_area", v)}
            options={usageAreaOptions}
          />
          <FilterSelect
            label={t("products.stockState")}
            value={filters.stock_state}
            onChange={(v) =>
              updateFilter("stock_state", v as Filters["stock_state"])
            }
            options={stockStateOptions}
          />
          {canReadAll && (
            <FilterSelect
              label={t("products.status")}
              value={filters.is_active}
              onChange={(v) =>
                updateFilter("is_active", v as Filters["is_active"])
              }
              options={[
                { value: "true", label: t("products.active") },
                { value: "false", label: t("products.inactive") },
              ]}
            />
          )}
          <FilterSelect
            label={t("products.featured")}
            value={filters.is_featured}
            onChange={(v) =>
              updateFilter("is_featured", v as Filters["is_featured"])
            }
            options={[
              { value: "true", label: t("products.yes") },
              { value: "false", label: t("products.no") },
            ]}
          />
          <Input
            aria-label={t("products.minimumPrice")}
            type="number"
            min="0"
            placeholder={t("products.minimumPrice")}
            value={filters.min_price}
            onChange={(event) => updateFilter("min_price", event.target.value)}
          />
          <Input
            aria-label={t("products.maximumPrice")}
            type="number"
            min="0"
            placeholder={t("products.maximumPrice")}
            value={filters.max_price}
            onChange={(event) => updateFilter("max_price", event.target.value)}
          />
        </div>
        <details className="mt-4 border-t border-outline-variant pt-3">
          <summary className="cursor-pointer text-label-large text-primary">
            {t("products.advancedFilters")}
          </summary>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <FilterSelect
              label={t("products.colorFamily")}
              value={filters.color_family}
              onChange={(v) => updateFilter("color_family", v)}
              options={colorOptions}
            />
            <Input
              aria-label={t("products.widthMm")}
              type="number"
              min="1"
              placeholder={t("products.widthMm")}
              value={filters.width_mm}
              onChange={(event) => updateFilter("width_mm", event.target.value)}
            />
            <Input
              aria-label={t("products.heightMm")}
              type="number"
              min="1"
              placeholder={t("products.heightMm")}
              value={filters.height_mm}
              onChange={(event) =>
                updateFilter("height_mm", event.target.value)
              }
            />
            <Input
              aria-label={t("products.thicknessMm")}
              type="number"
              min="1"
              placeholder={t("products.thicknessMm")}
              value={filters.thickness_mm}
              onChange={(event) =>
                updateFilter("thickness_mm", event.target.value)
              }
            />
          </div>
        </details>
      </section>

      <section
        className="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-low shadow-elevation-1"
        aria-label={t("products.title")}
      >
        <div className="flex items-center justify-between border-b border-outline-variant px-4 py-3">
          <p className="text-body-medium text-on-surface-variant">
            {query.data
              ? t("products.productCount", { count: query.data.count })
              : t("products.loading")}
          </p>
          {query.isFetching && !query.isPending && (
            <LoaderCircle
              className="size-4 animate-spin text-primary"
              aria-label={t("products.loading")}
            />
          )}
        </div>
        {query.isPending ? (
          <div
            className="grid min-h-64 place-items-center p-8 text-center"
            role="status"
          >
            <div className="flex flex-col items-center gap-3 text-on-surface-variant">
              <LoaderCircle className="size-8 animate-spin text-primary" />
              {t("products.loading")}
            </div>
          </div>
        ) : query.isError ? (
          <div
            className="grid min-h-64 place-items-center p-8 text-center"
            role="alert"
          >
            <div className="flex flex-col items-center gap-3">
              <p className="text-body-large text-on-surface">
                {t("products.loadError")}
              </p>
              <Button variant="outline" onClick={() => void query.refetch()}>
                {t("products.retry")}
              </Button>
            </div>
          </div>
        ) : !anyResults ? (
          <div className="grid min-h-64 place-items-center p-8 text-center">
            <div className="flex max-w-md flex-col items-center gap-3">
              <div className="rounded-full bg-secondary-container p-4 text-on-secondary-container">
                {search || activeFilterCount > 0 ? (
                  <Search className="size-8" />
                ) : (
                  <Package className="size-8" />
                )}
              </div>
              <h2 className="text-title-large text-on-surface">
                {search || activeFilterCount > 0
                  ? t("products.noMatches")
                  : t("products.emptyTitle")}
              </h2>
              <p className="text-body-medium text-on-surface-variant">
                {search || activeFilterCount > 0
                  ? t("products.noMatchesDescription")
                  : t("products.emptyDescription")}
              </p>
              {search || activeFilterCount > 0 ? (
                <Button variant="outline" onClick={clearFilters}>
                  {t("products.clearFilters")}
                </Button>
              ) : null}
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-surface-container-high hover:bg-surface-container-high">
                  <TableHead>{t("products.image")}</TableHead>
                  <TableHead>
                    <SortButton
                      label={t("products.nameSku")}
                      scopeLabel={t("products.sortCurrentPage")}
                      active={sort.key === "name"}
                      direction={sort.direction}
                      onClick={() => changeSort("name")}
                    />
                  </TableHead>
                  <TableHead>{t("products.category")}</TableHead>
                  <TableHead>{t("products.brand")}</TableHead>
                  <TableHead>{t("products.size")}</TableHead>
                  <TableHead>{t("products.finish")}</TableHead>
                  <TableHead>
                    <SortButton
                      label={t("products.price")}
                      scopeLabel={t("products.sortCurrentPage")}
                      active={sort.key === "price"}
                      direction={sort.direction}
                      onClick={() => changeSort("price")}
                    />
                  </TableHead>
                  <TableHead>
                    <SortButton
                      label={t("products.stock")}
                      scopeLabel={t("products.sortCurrentPage")}
                      active={sort.key === "stock_quantity"}
                      direction={sort.direction}
                      onClick={() => changeSort("stock_quantity")}
                    />
                  </TableHead>
                  <TableHead>{t("products.status")}</TableHead>
                  <TableHead>{t("products.featured")}</TableHead>
                  <TableHead>{t("common.actions")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedProducts.map((product) => (
                  <ProductRow
                    key={product.id}
                    product={product}
                    categoryName={
                      categories.find((item) => item.id === product.category_id)
                        ?.name ?? t("common.na")
                    }
                    brandName={
                      brands.find((item) => item.id === product.brand_id)
                        ?.name ?? t("common.na")
                    }
                    canUpdate={canUpdate}
                    canManageImages={canManageImages}
                    categories={categories}
                    brands={brands}
                    onDeactivate={() => deactivateMutation.mutate(product.id)}
                    isDeactivating={
                      deactivateMutation.isPending &&
                      deactivateMutation.variables === product.id
                    }
                    formatPrice={formatPrice}
                  />
                ))}
              </TableBody>
            </Table>
          </div>
        )}
        {query.data && query.data.count > 0 && (
          <div className="flex items-center justify-between border-t border-outline-variant px-4 py-3">
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
      </section>
    </div>
  )
}

function SortButton({
  label,
  scopeLabel,
  active,
  direction,
  onClick,
}: {
  label: string
  scopeLabel: string
  active: boolean
  direction: "asc" | "desc"
  onClick: () => void
}) {
  return (
    <button
      type="button"
      aria-description={scopeLabel}
      onClick={onClick}
      className="inline-flex items-center gap-1 font-medium text-on-surface hover:text-primary"
    >
      {label}
      <span aria-hidden="true">
        {active ? (direction === "asc" ? "↑" : "↓") : "↕"}
      </span>
    </button>
  )
}

function ProductRow({
  product,
  categoryName,
  brandName,
  canUpdate,
  canManageImages,
  categories,
  brands,
  onDeactivate,
  isDeactivating,
  formatPrice,
}: {
  product: ProductPublic
  categoryName: string
  brandName: string
  canUpdate: boolean
  canManageImages: boolean
  categories: CategoryPublic[]
  brands: BrandPublic[]
  onDeactivate: () => void
  isDeactivating: boolean
  formatPrice: (price?: string | null) => string
}) {
  const { t } = useTranslation()
  const stockVariant =
    product.stock_state === "out_of_stock"
      ? "destructive"
      : product.stock_state === "low_stock"
        ? "secondary"
        : "outline"
  const stockStateLabel = {
    in_stock: t("products.stockStates.in_stock"),
    low_stock: t("products.stockStates.low_stock"),
    out_of_stock: t("products.stockStates.out_of_stock"),
  }[product.stock_state as "in_stock" | "low_stock" | "out_of_stock"]
  const finishLabel = {
    matte: t("products.finishes.matte"),
    glossy: t("products.finishes.glossy"),
    polished: t("products.finishes.polished"),
    satin: t("products.finishes.satin"),
    textured: t("products.finishes.textured"),
    anti_slip: t("products.finishes.anti_slip"),
  }[product.finish ?? ""]
  return (
    <TableRow className="hover:bg-surface-container-high/60">
      <TableCell>
        <ProductImageThumbnail
          image={product.images?.find((image) => image.is_primary)}
          productId={product.id}
          alt={product.name}
          fallbackLabel={t("products.imagePlaceholder")}
          className="size-12"
        />
      </TableCell>
      <TableCell className="min-w-48">
        <div className="font-medium text-on-surface">{product.name}</div>
        <div className="font-mono text-label-small text-on-surface-variant">
          {product.sku}
        </div>
      </TableCell>
      <TableCell>{categoryName}</TableCell>
      <TableCell>{brandName}</TableCell>
      <TableCell className="whitespace-nowrap">
        {[product.width_mm, product.height_mm, product.thickness_mm]
          .filter(Boolean)
          .join(" × ") || t("common.na")}
      </TableCell>
      <TableCell>{finishLabel ?? product.finish ?? t("common.na")}</TableCell>
      <TableCell className="whitespace-nowrap">
        {formatPrice(product.price)}
      </TableCell>
      <TableCell>
        <div className="grid gap-1">
          <span>{product.stock_quantity ?? 0}</span>
          <Badge variant={stockVariant}>{stockStateLabel}</Badge>
        </div>
      </TableCell>
      <TableCell>
        <Badge variant={product.is_active ? "default" : "outline"}>
          {t(product.is_active ? "products.active" : "products.inactive")}
        </Badge>
      </TableCell>
      <TableCell>
        {product.is_featured ? (
          <Badge variant="secondary">{t("products.featured")}</Badge>
        ) : (
          <span className="text-on-surface-variant">—</span>
        )}
      </TableCell>
      <TableCell>
        {(canUpdate || canManageImages) && (
          <div className="flex items-center gap-2">
            <ProductFormDialog
              product={product}
              categories={categories}
              brands={brands}
              canCreate={false}
              canUpdate={canUpdate}
              canManageImages={canManageImages}
            />
            {product.is_active && (
              <Button
                variant="ghost"
                size="sm"
                disabled={isDeactivating}
                onClick={onDeactivate}
              >
                {t("products.deactivate")}
              </Button>
            )}
          </div>
        )}
      </TableCell>
    </TableRow>
  )
}
