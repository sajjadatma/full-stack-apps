import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Check, Plus } from "lucide-react"
import type { FormEvent } from "react"
import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"

import {
  type BrandPublic,
  type CategoryPublic,
  type ProductCreate,
  type ProductImagePublic,
  type ProductPublic,
  ProductsService,
  type ProductUpdate,
} from "@/client"
import {
  allowedImageTypes,
  ProductImagesEditor,
  type ProductImageUpload,
} from "@/components/Products/ProductImagesEditor"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

type Draft = {
  name: string
  sku: string
  slug: string
  description: string
  category_id: string
  brand_id: string
  product_type: string
  material: string
  finish: string
  usage_area: string
  color_family: string
  width_mm: string
  height_mm: string
  thickness_mm: string
  rectified: boolean
  anti_slip_rating: string
  water_absorption_percent: string
  pieces_per_box: string
  sqm_per_box: string
  kg_per_box: string
  country_of_origin: string
  price: string
  stock_quantity: string
  low_stock_threshold: string
  is_active: boolean
  is_featured: boolean
}

const emptyDraft = (): Draft => ({
  name: "",
  sku: "",
  slug: "",
  description: "",
  category_id: "",
  brand_id: "",
  product_type: "",
  material: "",
  finish: "",
  usage_area: "",
  color_family: "",
  width_mm: "",
  height_mm: "",
  thickness_mm: "",
  rectified: false,
  anti_slip_rating: "",
  water_absorption_percent: "",
  pieces_per_box: "",
  sqm_per_box: "",
  kg_per_box: "",
  country_of_origin: "",
  price: "",
  stock_quantity: "0",
  low_stock_threshold: "",
  is_active: true,
  is_featured: false,
})

function toDraft(product?: ProductPublic): Draft {
  if (!product) return emptyDraft()
  return {
    name: product.name,
    sku: product.sku,
    slug: product.slug,
    description: product.description ?? "",
    category_id: product.category_id,
    brand_id: product.brand_id ?? "",
    product_type: product.product_type ?? "",
    material: product.material ?? "",
    finish: product.finish ?? "",
    usage_area: product.usage_area ?? "",
    color_family: product.color_family ?? "",
    width_mm: product.width_mm?.toString() ?? "",
    height_mm: product.height_mm?.toString() ?? "",
    thickness_mm: product.thickness_mm?.toString() ?? "",
    rectified: product.rectified ?? false,
    anti_slip_rating: product.anti_slip_rating ?? "",
    water_absorption_percent:
      product.water_absorption_percent?.toString() ?? "",
    pieces_per_box: product.pieces_per_box?.toString() ?? "",
    sqm_per_box: product.sqm_per_box?.toString() ?? "",
    kg_per_box: product.kg_per_box?.toString() ?? "",
    country_of_origin: product.country_of_origin ?? "",
    price: product.price?.toString() ?? "",
    stock_quantity: product.stock_quantity?.toString() ?? "0",
    low_stock_threshold: product.low_stock_threshold?.toString() ?? "",
    is_active: product.is_active ?? true,
    is_featured: product.is_featured ?? false,
  }
}

const numberFields = [
  "width_mm",
  "height_mm",
  "thickness_mm",
  "water_absorption_percent",
  "pieces_per_box",
  "sqm_per_box",
  "kg_per_box",
  "price",
  "stock_quantity",
  "low_stock_threshold",
] as const

function payloadFromDraft(draft: Draft): ProductCreate {
  const payload: ProductCreate = {
    name: draft.name.trim(),
    sku: draft.sku.trim(),
    slug: draft.slug.trim(),
    category_id: draft.category_id,
    stock_quantity: Number(draft.stock_quantity || 0),
    rectified: draft.rectified,
    is_active: draft.is_active,
    is_featured: draft.is_featured,
  }
  const optionalTextFields = [
    "description",
    "product_type",
    "material",
    "finish",
    "usage_area",
    "color_family",
    "anti_slip_rating",
    "country_of_origin",
  ] as const
  for (const field of optionalTextFields) {
    const value = draft[field].trim()
    if (value) payload[field] = value
  }
  if (draft.brand_id) payload.brand_id = draft.brand_id
  for (const field of numberFields) {
    const value = draft[field].trim()
    if (!value) continue
    switch (field) {
      case "width_mm":
        payload.width_mm = Number(value)
        break
      case "height_mm":
        payload.height_mm = Number(value)
        break
      case "thickness_mm":
        payload.thickness_mm = Number(value)
        break
      case "pieces_per_box":
        payload.pieces_per_box = Number(value)
        break
      case "stock_quantity":
        payload.stock_quantity = Number(value)
        break
      case "low_stock_threshold":
        payload.low_stock_threshold = Number(value)
        break
      case "water_absorption_percent":
        payload.water_absorption_percent = value
        break
      case "sqm_per_box":
        payload.sqm_per_box = value
        break
      case "kg_per_box":
        payload.kg_per_box = value
        break
      case "price":
        payload.price = value
        break
    }
  }
  return payload
}

function updatePayloadFromDraft(draft: Draft): ProductUpdate {
  const payload = payloadFromDraft(draft)
  return {
    ...payload,
    description: draft.description.trim() || null,
    brand_id: draft.brand_id || null,
    product_type: draft.product_type.trim() || null,
    material: draft.material.trim() || null,
    finish: draft.finish.trim() || null,
    usage_area: draft.usage_area.trim() || null,
    color_family: draft.color_family.trim() || null,
    width_mm: draft.width_mm ? Number(draft.width_mm) : null,
    height_mm: draft.height_mm ? Number(draft.height_mm) : null,
    thickness_mm: draft.thickness_mm ? Number(draft.thickness_mm) : null,
    anti_slip_rating: draft.anti_slip_rating.trim() || null,
    water_absorption_percent: draft.water_absorption_percent || null,
    pieces_per_box: draft.pieces_per_box ? Number(draft.pieces_per_box) : null,
    sqm_per_box: draft.sqm_per_box || null,
    kg_per_box: draft.kg_per_box || null,
    country_of_origin: draft.country_of_origin.trim() || null,
    price: draft.price || null,
    low_stock_threshold: draft.low_stock_threshold
      ? Number(draft.low_stock_threshold)
      : null,
  }
}

function TextField({
  label,
  value,
  onChange,
  required = false,
  type = "text",
  min,
  step,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  required?: boolean
  type?: string
  min?: string
  step?: string
}) {
  const inputId = `product-field-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`
  return (
    <div className="grid gap-1.5 text-label-large text-on-surface">
      <span>
        <label htmlFor={inputId}>{label}</label>
        {required && <span className="text-destructive"> *</span>}
      </span>
      <Input
        id={inputId}
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required={required}
        min={min}
        step={step}
      />
    </div>
  )
}

function SelectField({
  label,
  value,
  onChange,
  options,
  placeholder,
  required = false,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  options: { value: string; label: string }[]
  placeholder: string
  required?: boolean
}) {
  const selectId = `product-field-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`
  return (
    <div className="grid gap-1.5 text-label-large text-on-surface">
      <span>
        <label htmlFor={selectId}>{label}</label>
        {required && <span className="text-destructive"> *</span>}
      </span>
      <select
        id={selectId}
        className="h-11 w-full rounded-xs border border-outline bg-surface px-3 text-body-medium focus-visible:border-primary focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-primary/25"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required={required}
      >
        {!required && <option value="">{placeholder}</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  )
}

function CheckField({
  label,
  checked,
  onChange,
}: {
  label: string
  checked: boolean
  onChange: (checked: boolean) => void
}) {
  return (
    <label className="flex min-h-11 items-center gap-3 rounded-md border border-outline-variant px-3 text-body-medium text-on-surface">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="size-4 accent-primary"
      />
      {label}
    </label>
  )
}

interface ProductFormDialogProps {
  categories: CategoryPublic[]
  brands: BrandPublic[]
  product?: ProductPublic
  canCreate: boolean
  canUpdate: boolean
  canManageImages: boolean
}

export function ProductFormDialog({
  categories,
  brands,
  product,
  canCreate,
  canUpdate,
  canManageImages,
}: ProductFormDialogProps) {
  const { t } = useTranslation()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState<Draft>(() => toDraft(product))
  const [createdProduct, setCreatedProduct] = useState<ProductPublic>()
  const [images, setImages] = useState<ProductImagePublic[]>(
    product?.images ?? [],
  )
  const [uploads, setUploads] = useState<ProductImageUpload[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [isLoadingImages, setIsLoadingImages] = useState(
    Boolean(product && canManageImages),
  )
  const productRef = useRef(product)
  const showErrorToastRef = useRef(showErrorToast)
  productRef.current = product
  showErrorToastRef.current = showErrorToast
  const savedProduct = product ?? createdProduct
  const editing = Boolean(savedProduct)
  const canEditDetails = product
    ? canUpdate
    : createdProduct
      ? canUpdate
      : canCreate
  const hasUnfinishedUploads = uploads.some(
    (upload) => upload.status === "queued" || upload.status === "failed",
  )

  useEffect(() => {
    if (!open) return
    const currentProduct = productRef.current
    setDraft(toDraft(currentProduct))
    setCreatedProduct(undefined)
    setImages(currentProduct?.images ?? [])
    setUploads([])
    if (currentProduct && canManageImages) {
      setIsLoadingImages(true)
      let active = true
      void ProductsService.readProduct({
        path: { product_id: currentProduct.id },
      })
        .then((response) => {
          if (active) {
            setImages(response.data.images ?? [])
            queryClient.setQueryData(
              ["product-detail", currentProduct.id],
              response.data,
            )
          }
        })
        .catch((error) =>
          handleError.bind(showErrorToastRef.current)(error as Error),
        )
        .finally(() => {
          if (active) setIsLoadingImages(false)
        })
      return () => {
        active = false
      }
    }
  }, [open, canManageImages, queryClient])

  const uploadFiles = async (productId: string, uploadIds?: string[]) => {
    const pending = uploads.filter(
      (upload) =>
        (upload.status === "queued" || upload.status === "failed") &&
        (!uploadIds || uploadIds.includes(upload.id)),
    )
    if (pending.length === 0) return false
    setIsUploading(true)
    let hadFailure = false
    try {
      for (const upload of pending) {
        setUploads((current) =>
          current.map((item) =>
            item.id === upload.id ? { ...item, status: "uploading" } : item,
          ),
        )
        if (!allowedImageTypes.has(upload.file.type)) {
          hadFailure = true
          setUploads((current) =>
            current.map((item) =>
              item.id === upload.id ? { ...item, status: "failed" } : item,
            ),
          )
          showErrorToast(
            t("products.images.invalidFormat", { file: upload.file.name }),
          )
          continue
        }
        try {
          const response = await ProductsService.uploadProductImage({
            path: { product_id: productId },
            body: { file: upload.file, alt_text: upload.file.name },
          })
          const refreshed = await ProductsService.readProduct({
            path: { product_id: productId },
          })
          await queryClient.cancelQueries({
            queryKey: ["product-detail", productId],
          })
          queryClient.setQueryData(
            ["product-detail", productId],
            refreshed.data,
          )
          setImages(refreshed.data.images ?? [response.data])
          setUploads((current) =>
            current.map((item) =>
              item.id === upload.id ? { ...item, status: "success" } : item,
            ),
          )
          await queryClient.invalidateQueries({ queryKey: ["products"] })
        } catch (error) {
          hadFailure = true
          setUploads((current) =>
            current.map((item) =>
              item.id === upload.id ? { ...item, status: "failed" } : item,
            ),
          )
          handleError.bind(showErrorToast)(error as Error)
        }
      }
    } finally {
      setIsUploading(false)
    }
    return hadFailure
  }

  const mutation = useMutation({
    mutationFn: async (payload: ProductCreate) => {
      if (product) {
        return (
          await ProductsService.updateProduct({
            path: { product_id: product.id },
            body: updatePayloadFromDraft(draft),
          })
        ).data
      }
      if (createdProduct) {
        if (!canUpdate) return createdProduct
        return (
          await ProductsService.updateProduct({
            path: { product_id: createdProduct.id },
            body: updatePayloadFromDraft(draft),
          })
        ).data
      }
      return (await ProductsService.createProduct({ body: payload })).data
    },
    onSuccess: async (saved) => {
      if (!product) setCreatedProduct(saved)
      setImages(saved.images ?? [])
      const failedUploads = canManageImages
        ? await uploadFiles(saved.id)
        : false
      void queryClient.invalidateQueries({ queryKey: ["products"] })
      if (failedUploads) return
      showSuccessToast(
        t(editing ? "products.updatedSuccess" : "products.createdSuccess"),
      )
      setOpen(false)
    },
    onError: handleError.bind(showErrorToast),
  })

  const update = <K extends keyof Draft>(field: K, value: Draft[K]) =>
    setDraft((current) => ({ ...current, [field]: value }))

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!canEditDetails) return
    mutation.mutate(payloadFromDraft(draft))
  }

  const addUploads = (files: File[]) => {
    setUploads((current) => [
      ...current,
      ...files.map((file) => ({
        id: crypto.randomUUID(),
        file,
        status: "queued" as const,
      })),
    ])
  }

  const retryUpload = async (uploadId: string) => {
    if (!savedProduct) return
    const failed = await uploadFiles(savedProduct.id, [uploadId])
    const unfinished = uploads.some(
      (upload) =>
        upload.id !== uploadId &&
        (upload.status === "queued" || upload.status === "failed"),
    )
    if (!failed && !unfinished) setOpen(false)
  }

  const onOpenChange = (nextOpen: boolean) => {
    if (
      !nextOpen &&
      (mutation.isPending || isUploading || hasUnfinishedUploads)
    ) {
      return
    }
    setOpen(nextOpen)
  }

  if ((!product && !canCreate) || (product && !canUpdate && !canManageImages)) {
    return null
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {!product && canCreate && (
        <DialogTrigger asChild>
          <Button>
            <Plus className="me-2 size-4" />
            {t("products.addProduct")}
          </Button>
        </DialogTrigger>
      )}
      {product && (canUpdate || canManageImages) && (
        <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
          {canUpdate ? t("common.edit") : t("products.images.manage")}
        </Button>
      )}
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>
            {t(editing ? "products.editProduct" : "products.addProduct")}
          </DialogTitle>
          <DialogDescription>{t("products.formDescription")}</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="grid gap-5">
          <fieldset disabled={!canEditDetails} className="contents">
            <section className="grid gap-4 border-b border-outline-variant pb-5">
              <h3 className="text-title-medium">{t("products.identity")}</h3>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <TextField
                  label={t("products.name")}
                  value={draft.name}
                  onChange={(v) => update("name", v)}
                  required
                />
                <TextField
                  label={t("products.sku")}
                  value={draft.sku}
                  onChange={(v) => update("sku", v)}
                  required
                />
                <TextField
                  label={t("products.slug")}
                  value={draft.slug}
                  onChange={(v) => update("slug", v)}
                  required
                />
                <SelectField
                  label={t("products.category")}
                  value={draft.category_id}
                  onChange={(v) => update("category_id", v)}
                  options={categories.map((category) => ({
                    value: category.id,
                    label: category.name,
                  }))}
                  placeholder={t("products.selectCategory")}
                  required
                />
                <SelectField
                  label={t("products.brand")}
                  value={draft.brand_id}
                  onChange={(v) => update("brand_id", v)}
                  options={brands.map((brand) => ({
                    value: brand.id,
                    label: brand.name,
                  }))}
                  placeholder={t("products.noBrand")}
                />
                <TextField
                  label={t("products.productType")}
                  value={draft.product_type}
                  onChange={(v) => update("product_type", v)}
                />
              </div>
              <label className="grid gap-1.5 text-label-large text-on-surface">
                {t("products.description")}
                <textarea
                  className="min-h-24 rounded-xs border border-outline bg-transparent px-4 py-3 text-body-medium outline-none focus-visible:border-primary focus-visible:ring-[3px] focus-visible:ring-primary/25"
                  value={draft.description}
                  onChange={(event) =>
                    update("description", event.target.value)
                  }
                />
              </label>
            </section>

            <section className="grid gap-4 border-b border-outline-variant pb-5">
              <h3 className="text-title-medium">
                {t("products.specifications")}
              </h3>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <TextField
                  label={t("products.material")}
                  value={draft.material}
                  onChange={(v) => update("material", v)}
                />
                <TextField
                  label={t("products.finish")}
                  value={draft.finish}
                  onChange={(v) => update("finish", v)}
                />
                <TextField
                  label={t("products.usageArea")}
                  value={draft.usage_area}
                  onChange={(v) => update("usage_area", v)}
                />
                <TextField
                  label={t("products.colorFamily")}
                  value={draft.color_family}
                  onChange={(v) => update("color_family", v)}
                />
                <TextField
                  label={t("products.widthMm")}
                  type="number"
                  min="1"
                  value={draft.width_mm}
                  onChange={(v) => update("width_mm", v)}
                />
                <TextField
                  label={t("products.heightMm")}
                  type="number"
                  min="1"
                  value={draft.height_mm}
                  onChange={(v) => update("height_mm", v)}
                />
                <TextField
                  label={t("products.thicknessMm")}
                  type="number"
                  min="1"
                  value={draft.thickness_mm}
                  onChange={(v) => update("thickness_mm", v)}
                />
                <TextField
                  label={t("products.antiSlipRating")}
                  value={draft.anti_slip_rating}
                  onChange={(v) => update("anti_slip_rating", v)}
                />
                <TextField
                  label={t("products.waterAbsorption")}
                  type="number"
                  min="0"
                  step="0.01"
                  value={draft.water_absorption_percent}
                  onChange={(v) => update("water_absorption_percent", v)}
                />
                <TextField
                  label={t("products.countryOfOrigin")}
                  value={draft.country_of_origin}
                  onChange={(v) => update("country_of_origin", v)}
                />
                <TextField
                  label={t("products.piecesPerBox")}
                  type="number"
                  min="1"
                  value={draft.pieces_per_box}
                  onChange={(v) => update("pieces_per_box", v)}
                />
                <TextField
                  label={t("products.sqmPerBox")}
                  type="number"
                  min="0"
                  step="0.001"
                  value={draft.sqm_per_box}
                  onChange={(v) => update("sqm_per_box", v)}
                />
                <TextField
                  label={t("products.kgPerBox")}
                  type="number"
                  min="0"
                  step="0.001"
                  value={draft.kg_per_box}
                  onChange={(v) => update("kg_per_box", v)}
                />
              </div>
              <CheckField
                label={t("products.rectified")}
                checked={draft.rectified}
                onChange={(v) => update("rectified", v)}
              />
            </section>

            <section className="grid gap-4">
              <h3 className="text-title-medium">
                {t("products.stockAndPricing")}
              </h3>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <TextField
                  label={t("products.price")}
                  type="number"
                  min="0"
                  step="0.01"
                  value={draft.price}
                  onChange={(v) => update("price", v)}
                />
                <TextField
                  label={t("products.stockQuantity")}
                  type="number"
                  min="0"
                  value={draft.stock_quantity}
                  onChange={(v) => update("stock_quantity", v)}
                  required
                />
                <TextField
                  label={t("products.lowStockThreshold")}
                  type="number"
                  min="0"
                  value={draft.low_stock_threshold}
                  onChange={(v) => update("low_stock_threshold", v)}
                />
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <CheckField
                  label={t("products.active")}
                  checked={draft.is_active}
                  onChange={(v) => update("is_active", v)}
                />
                <CheckField
                  label={t("products.featured")}
                  checked={draft.is_featured}
                  onChange={(v) => update("is_featured", v)}
                />
              </div>
            </section>
          </fieldset>

          {canManageImages && (
            <ProductImagesEditor
              productId={savedProduct?.id}
              images={images}
              uploads={uploads}
              uploading={isUploading}
              loading={isLoadingImages}
              onImagesChange={setImages}
              onQueueFiles={addUploads}
              onRemoveUpload={(uploadId) =>
                setUploads((current) =>
                  current.filter((upload) => upload.id !== uploadId),
                )
              }
              onUploadFiles={() => {
                if (savedProduct) void uploadFiles(savedProduct.id)
              }}
              onRetryUpload={(uploadId) => void retryUpload(uploadId)}
            />
          )}
          <DialogFooter className="sticky bottom-0 -mx-6 -mb-6 border-t border-outline-variant bg-surface-container-high p-6">
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
              disabled={
                mutation.isPending || isUploading || hasUnfinishedUploads
              }
            >
              {t("common.cancel")}
            </Button>
            {canEditDetails && (
              <LoadingButton
                type="submit"
                loading={mutation.isPending || isUploading}
                disabled={isUploading}
              >
                <Check className="me-2 size-4" />
                {t("common.save")}
              </LoadingButton>
            )}
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
