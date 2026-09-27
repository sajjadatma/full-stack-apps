import { useEffect, useState } from "react"

/**
 * Create an object URL for a Blob and revoke it when the Blob changes or the
 * component unmounts. Keeps authenticated image/result bytes out of the URL.
 */
export function useObjectUrl(blob?: Blob | null): string {
  const [url, setUrl] = useState("")

  useEffect(() => {
    if (!blob) {
      setUrl("")
      return
    }
    const objectUrl = URL.createObjectURL(blob)
    setUrl(objectUrl)
    return () => URL.revokeObjectURL(objectUrl)
  }, [blob])

  return url
}
