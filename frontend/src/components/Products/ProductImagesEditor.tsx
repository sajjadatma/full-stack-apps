import { useQueryClient } from "@tanstack/react-query"
import {
  ArrowDown,
  ArrowUp,
  LoaderCircle,
  Star,
  Trash2,
  Upload,
} from "lucide-react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"

import { type ProductImagePublic, ProductsService } from "@/client"
import { ProductImageThumbnail } from "@/components/Products/ProductImageThumbnail"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

export type ProductImageUpload = {
  id: string
  file: File
  status: "queued" | "uploading" | "success" | "failed"
}

const allowedImageTypes = new Set(["image/jpeg", "image/png", "image/webp"])

function UploadPreview({ file }: { file: File }) {
  const [source, setSource] = useState("")

  useEffect(() => {
    const objectUrl = URL.createObjectURL(file)
    setSource(objectUrl)
    return () => URL.revokeObjectURL(objectUrl)
  }, [file])

  return source ? (
    <img
      src={source}
      alt={file.name}
      className="size-12 rounded-md object-cover"
    />
  ) : null
}

export function ProductImagesEditor({
  productId,
  images,
  uploads,
  uploading,
  loading,
  onImagesChange,
  onQueueFiles,
  onRemoveUpload,
  onUploadFiles,
  onRetryUpload,
}: {
  productId?: string
  images: ProductImagePublic[]
  uploads: ProductImageUpload[]
  uploading: boolean
  loading: boolean
  onImagesChange: (images: ProductImagePublic[]) => void
  onQueueFiles: (files: File[]) => void
  onRemoveUpload: (uploadId: string) => void
  onUploadFiles: () => void
  onRetryUpload: (uploadId: string) => void
}) {
  const { t } = useTranslation()
  const { showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [orderedImages, setOrderedImages] = useState(images)
  const [actionImageId, setActionImageId] = useState<string>()

  useEffect(() => {
    setOrderedImages(sortImages(images))
  }, [images])

  const refreshImages = async () => {
    if (!productId) return
    const response = await ProductsService.readProduct({
      path: { product_id: productId },
    })
    const nextImages = sortImages(response.data.images ?? [])
    await queryClient.cancelQueries({ queryKey: ["product-detail", productId] })
    queryClient.setQueryData(["product-detail", productId], response.data)
    await queryClient.invalidateQueries({
      queryKey: ["product-detail", productId],
    })
    setOrderedImages(nextImages)
    onImagesChange(nextImages)
    await queryClient.invalidateQueries({ queryKey: ["products"] })
  }

  const runImageAction = async (
    imageId: string,
    action: () => Promise<unknown>,
  ) => {
    if (!productId || actionImageId || uploading || loading) return
    setActionImageId(imageId)
    try {
      await action()
      await refreshImages()
    } catch (error) {
      handleError.bind(showErrorToast)(error as Error)
    } finally {
      setActionImageId(undefined)
    }
  }

  const setPrimary = (imageId: string) =>
    runImageAction(imageId, () =>
      ProductsService.setPrimaryProductImage({
        path: { product_id: productId!, image_id: imageId },
      }),
    )

  const reorder = async (imageId: string, direction: -1 | 1) => {
    if (!productId || actionImageId || uploading || loading) return
    const currentImages = orderedImages
    const from = currentImages.findIndex((image) => image.id === imageId)
    const to = from + direction
    if (from < 0 || to < 0 || to >= currentImages.length) return
    const reordered = [...currentImages]
    ;[reordered[from], reordered[to]] = [reordered[to], reordered[from]]
    setOrderedImages(reordered)
    setActionImageId(imageId)
    try {
      await ProductsService.reorderProductImages({
        path: { product_id: productId },
        body: { image_ids: reordered.map((image) => image.id) },
      })
      await refreshImages()
    } catch (error) {
      setOrderedImages(currentImages)
      handleError.bind(showErrorToast)(error as Error)
    } finally {
      setActionImageId(undefined)
    }
  }

  const deleteImage = async (image: ProductImagePublic) => {
    if (!productId || actionImageId || uploading || loading) return
    const confirmed = window.confirm(
      t("products.images.confirmDelete", {
        image: image.alt_text || t("products.images.unnamedImage"),
      }),
    )
    if (!confirmed) return
    await runImageAction(image.id, () =>
      ProductsService.deleteProductImage({
        path: { product_id: productId, image_id: image.id },
      }),
    )
  }

  const queuedCount = uploads.filter(
    (upload) => upload.status === "queued" || upload.status === "failed",
  ).length

  return (
    <section
      className="grid gap-4 border-t border-outline-variant pt-5"
      aria-label={t("products.images.title")}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-title-medium">{t("products.images.title")}</h3>
          <p className="text-body-small text-on-surface-variant">
            {t("products.images.formats")}
          </p>
        </div>
        <label className="inline-flex h-9 cursor-pointer items-center justify-center gap-2 rounded-full border border-outline px-4 text-body-medium text-primary hover:bg-primary/8 has-[:disabled]:pointer-events-none has-[:disabled]:opacity-40">
          <Upload className="size-4" />
          {t("products.images.chooseFiles")}
          <input
            className="sr-only"
            aria-label={t("products.images.inputLabel")}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            disabled={uploading || loading}
            onChange={(event) => {
              onQueueFiles(Array.from(event.target.files ?? []))
              event.currentTarget.value = ""
            }}
          />
        </label>
      </div>

      {uploads.length > 0 && (
        <ul
          className="grid gap-2"
          aria-label={t("products.images.uploadQueue")}
        >
          {uploads.map((upload) => (
            <li
              key={upload.id}
              className="flex flex-wrap items-center gap-3 rounded-lg border border-outline-variant p-2"
            >
              <UploadPreview file={upload.file} />
              <span className="min-w-32 flex-1 truncate text-body-medium">
                {upload.file.name}
              </span>
              {upload.status === "uploading" && (
                <progress
                  aria-label={t("products.images.uploading", {
                    file: upload.file.name,
                  })}
                  className="h-2 w-20 accent-primary"
                />
              )}
              <span
                className={`text-label-medium ${upload.status === "failed" ? "text-error" : "text-on-surface-variant"}`}
              >
                {t(`products.images.states.${upload.status}`)}
              </span>
              {upload.status === "failed" && productId && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={uploading || loading}
                  aria-label={t("products.images.retryFile", {
                    file: upload.file.name,
                  })}
                  onClick={() => onRetryUpload(upload.id)}
                >
                  {t("products.images.retry")}
                </Button>
              )}
              {(upload.status === "queued" || upload.status === "failed") && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  disabled={uploading || loading}
                  aria-label={t("products.images.removeQueuedFile", {
                    file: upload.file.name,
                  })}
                  onClick={() => onRemoveUpload(upload.id)}
                >
                  <Trash2 />
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}

      {!productId && uploads.some((upload) => upload.status !== "success") && (
        <p className="text-body-small text-on-surface-variant">
          {t("products.images.saveProductFirst")}
        </p>
      )}
      {productId && queuedCount > 0 && (
        <Button
          type="button"
          variant="secondary"
          className="justify-self-start"
          disabled={uploading || loading}
          onClick={onUploadFiles}
        >
          {uploading ? <LoaderCircle className="animate-spin" /> : <Upload />}
          {t("products.images.uploadFiles", { count: queuedCount })}
        </Button>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {orderedImages.map((image, index) => (
          <article
            key={image.id}
            data-testid="product-image-item"
            className="grid gap-2 rounded-lg border border-outline-variant p-3"
          >
            <ProductImageThumbnail
              image={image}
              alt={image.alt_text || t("products.images.productImage")}
              fallbackLabel={t("products.images.productImage")}
              className="h-28 w-full"
            />
            <div className="flex items-center justify-between gap-2">
              <span
                className="truncate text-body-small"
                title={image.alt_text ?? ""}
              >
                {image.alt_text || t("products.images.productImage")}
              </span>
              {image.is_primary ? (
                <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-primary-container px-2 py-1 text-label-small text-on-primary-container">
                  <Star className="size-3" />
                  {t("products.images.primary")}
                </span>
              ) : (
                <span className="text-label-small text-on-surface-variant">
                  {t("products.images.additional")}
                </span>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-1">
              {!image.is_primary && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={Boolean(actionImageId) || uploading || loading}
                  onClick={() => void setPrimary(image.id)}
                >
                  <Star />
                  {t("products.images.setPrimary")}
                </Button>
              )}
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label={t("products.images.moveUp", {
                  image: image.alt_text || t("products.images.productImage"),
                })}
                disabled={
                  index === 0 || Boolean(actionImageId) || uploading || loading
                }
                onClick={() => void reorder(image.id, -1)}
              >
                <ArrowUp />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label={t("products.images.moveDown", {
                  image: image.alt_text || t("products.images.productImage"),
                })}
                disabled={
                  index === orderedImages.length - 1 ||
                  Boolean(actionImageId) ||
                  uploading ||
                  loading
                }
                onClick={() => void reorder(image.id, 1)}
              >
                <ArrowDown />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label={t("products.images.deleteImage", {
                  image: image.alt_text || t("products.images.productImage"),
                })}
                disabled={Boolean(actionImageId) || uploading || loading}
                onClick={() => void deleteImage(image)}
              >
                <Trash2 />
              </Button>
              {actionImageId === image.id && (
                <LoaderCircle
                  className="size-4 animate-spin text-primary"
                  aria-label={t("products.images.updating")}
                />
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

function sortImages(images: ProductImagePublic[]) {
  return [...images].sort(
    (left, right) =>
      (left.sort_order ?? 0) - (right.sort_order ?? 0) ||
      left.id.localeCompare(right.id),
  )
}

export { allowedImageTypes }
