import { useMutation } from "@tanstack/react-query"
import { ImagePlus } from "lucide-react"
import { useRef, useState } from "react"
import { useTranslation } from "react-i18next"

import { VisualizationProjectsService } from "@/client"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { useObjectUrl } from "@/hooks/useObjectUrl"
import { handleError } from "@/utils"

const ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/webp"]
const MAX_SIZE_BYTES = 10 * 1024 * 1024

export function RoomPhotoStep({
  onUploaded,
}: {
  onUploaded: (projectId: string) => void
}) {
  const { t } = useTranslation()
  const { showErrorToast } = useCustomToast()
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const preview = useObjectUrl(file)

  const uploadMutation = useMutation({
    mutationFn: async (selected: File) =>
      (
        await VisualizationProjectsService.projectsCreateVisualizationProject({
          body: { file: selected },
        })
      ).data,
    onSuccess: (project) => {
      onUploaded(project.id)
    },
    onError: handleError.bind(showErrorToast),
  })

  const selectFile = (selected: File | undefined) => {
    setError(null)
    if (!selected) return
    if (!ACCEPTED_TYPES.includes(selected.type)) {
      setError(t("visualizer.upload.invalidType"))
      return
    }
    if (selected.size > MAX_SIZE_BYTES) {
      setError(t("visualizer.upload.tooLarge"))
      return
    }
    setFile(selected)
  }

  return (
    <section
      className="flex flex-col gap-4"
      aria-labelledby="visualizer-upload-heading"
      data-testid="visualizer-step-upload"
    >
      <div>
        <h2
          id="visualizer-upload-heading"
          className="text-title-large text-on-surface"
        >
          {t("visualizer.upload.title")}
        </h2>
        <p className="mt-1 text-body-medium text-on-surface-variant">
          {t("visualizer.upload.description")}
        </p>
      </div>

      <label
        className="flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-outline-variant bg-surface-container-low p-8 text-center transition-colors hover:border-primary"
        htmlFor="visualizer-room-photo"
      >
        {preview ? (
          <img
            src={preview}
            alt={t("visualizer.upload.previewAlt")}
            className="max-h-72 w-auto rounded-lg object-contain"
          />
        ) : (
          <>
            <span className="rounded-full bg-secondary-container p-4 text-on-secondary-container">
              <ImagePlus className="size-8" aria-hidden="true" />
            </span>
            <span className="text-title-medium text-on-surface">
              {t("visualizer.upload.cta")}
            </span>
            <span className="text-body-small text-on-surface-variant">
              {t("visualizer.upload.hint")}
            </span>
          </>
        )}
        <input
          ref={inputRef}
          id="visualizer-room-photo"
          data-testid="room-photo-input"
          type="file"
          accept={ACCEPTED_TYPES.join(",")}
          className="sr-only"
          onChange={(event) => selectFile(event.target.files?.[0])}
        />
      </label>

      {error && (
        <p role="alert" className="text-body-medium text-error">
          {error}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={() => inputRef.current?.click()}
        >
          {file ? t("visualizer.upload.change") : t("visualizer.upload.browse")}
        </Button>
        <LoadingButton
          type="button"
          loading={uploadMutation.isPending}
          disabled={!file}
          data-testid="room-photo-continue"
          onClick={() => file && uploadMutation.mutate(file)}
        >
          {t("common.continue")}
        </LoadingButton>
      </div>
    </section>
  )
}
