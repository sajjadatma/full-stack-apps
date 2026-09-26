import { useQuery } from "@tanstack/react-query"
import { Image as ImageIcon } from "lucide-react"
import { useEffect, useState } from "react"

import {
  type ProductImagePublic,
  ProductImagesService,
  ProductsService,
} from "@/client"

export function ProductImageThumbnail({
  image,
  productId,
  alt,
  className,
  fallbackLabel,
}: {
  image?: ProductImagePublic
  productId?: string
  alt: string
  className: string
  fallbackLabel: string
}) {
  const { data: product } = useQuery({
    queryKey: ["product-detail", productId],
    queryFn: async () =>
      (
        await ProductsService.readProduct({
          path: { product_id: productId! },
        })
      ).data,
    enabled: Boolean(productId),
  })
  const primaryImage = product
    ? product.images?.find((item) => item.is_primary)
    : image
  const { data } = useQuery({
    queryKey: ["product-image-content", primaryImage?.id],
    queryFn: async () =>
      (
        await ProductImagesService.imagesReadProductImageContent({
          path: { image_id: primaryImage!.id },
        })
      ).data,
    enabled: Boolean(primaryImage),
    staleTime: Number.POSITIVE_INFINITY,
  })
  const [source, setSource] = useState("")

  useEffect(() => {
    if (!data) {
      setSource("")
      return
    }
    const objectUrl = URL.createObjectURL(data)
    setSource(objectUrl)
    return () => URL.revokeObjectURL(objectUrl)
  }, [data])

  if (!source) {
    return (
      <div
        className={`grid place-items-center rounded-md bg-surface-container-high text-on-surface-variant ${className}`}
        role="img"
        aria-label={fallbackLabel}
      >
        <ImageIcon className="size-5" />
      </div>
    )
  }

  return (
    <img
      className={`rounded-md object-cover ${className}`}
      src={source}
      alt={alt}
    />
  )
}
