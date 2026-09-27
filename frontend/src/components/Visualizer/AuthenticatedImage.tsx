import { useQuery } from "@tanstack/react-query"
import { Image as ImageIcon } from "lucide-react"

import { useObjectUrl } from "@/hooks/useObjectUrl"

/**
 * Load an authenticated image (room photo or generated result) as a Blob and
 * render it from a temporary object URL that is revoked on unmount.
 */
export function AuthenticatedImage({
  queryKey,
  queryFn,
  alt,
  className,
  fallbackLabel,
}: {
  queryKey: unknown[]
  queryFn: () => Promise<Blob>
  alt: string
  className?: string
  fallbackLabel: string
}) {
  const { data } = useQuery({
    queryKey,
    queryFn,
    staleTime: Number.POSITIVE_INFINITY,
    retry: false,
  })
  const url = useObjectUrl(data)

  if (!url) {
    return (
      <div
        className={`grid place-items-center rounded-lg bg-surface-container-high text-on-surface-variant ${className ?? ""}`}
        role="img"
        aria-label={fallbackLabel}
      >
        <ImageIcon className="size-6" />
      </div>
    )
  }

  return <img src={url} alt={alt} className={className} />
}
