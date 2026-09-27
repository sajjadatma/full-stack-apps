import { useMutation } from "@tanstack/react-query"
import {
  createFileRoute,
  redirect,
  useNavigate,
  useSearch,
} from "@tanstack/react-router"
import { type ReactNode, useCallback } from "react"
import { useTranslation } from "react-i18next"

import { GenerationsService, UsersService } from "@/client"
import {
  isSurface,
  resolveStep,
  type VisualizerSearch,
  type VisualizerSurface,
  visualizerSearchSchema,
} from "@/components/Visualizer/flow"
import { GenerateStep } from "@/components/Visualizer/GenerateStep"
import { ProductStep } from "@/components/Visualizer/ProductStep"
import { ResultStep } from "@/components/Visualizer/ResultStep"
import { ReviewStep } from "@/components/Visualizer/ReviewStep"
import { RoomPhotoStep } from "@/components/Visualizer/RoomPhotoStep"
import { SurfaceStep } from "@/components/Visualizer/SurfaceStep"
import { VisualizerStepper } from "@/components/Visualizer/VisualizerStepper"
import useCustomToast from "@/hooks/useCustomToast"
import i18n from "@/i18n"
import { handleError } from "@/utils"

export const Route = createFileRoute("/_layout/visualizer")({
  component: VisualizerPage,
  validateSearch: visualizerSearchSchema,
  beforeLoad: async ({ search }) => {
    const { data: user } = await UsersService.readUserMe()
    const permissions = user.permissions ?? []
    const canUse =
      permissions.includes("generations.create") &&
      permissions.includes("generations.read_own") &&
      (permissions.includes("products.read") ||
        permissions.includes("products.read_any"))
    if (!canUse) throw redirect({ to: "/" })

    const resolved = resolveStep(search)
    if (search.step !== resolved) {
      throw redirect({
        to: "/visualizer",
        search: { ...search, step: resolved },
      })
    }
  },
  head: () => ({ meta: [{ title: i18n.t("meta.visualizer") }] }),
})

function VisualizerPage() {
  const { t } = useTranslation()
  const search = useSearch({ from: "/_layout/visualizer" })
  const navigate = useNavigate()
  const { showErrorToast } = useCustomToast()
  const step = resolveStep(search)

  const patch = useCallback(
    (next: Partial<VisualizerSearch>) => {
      void navigate({
        to: "/visualizer",
        search: (prev) => ({ ...prev, ...next }),
      })
    },
    [navigate],
  )

  const generateMutation = useMutation({
    mutationFn: async (input: {
      projectId: string
      productId: string
      surface: VisualizerSurface
    }) =>
      (
        await GenerationsService.createGeneration({
          body: {
            visualization_project_id: input.projectId,
            selected_product_id: input.productId,
            target_surface: input.surface,
          },
        })
      ).data,
    onSuccess: (job) => patch({ step: "generate", job: job.id }),
    onError: handleError.bind(showErrorToast),
  })

  const retryMutation = useMutation({
    mutationFn: async (jobId: string) =>
      (
        await GenerationsService.retryGeneration({
          path: { job_id: jobId },
        })
      ).data,
    onSuccess: (job) => patch({ step: "generate", job: job.id }),
    onError: handleError.bind(showErrorToast),
  })

  const startNew = () =>
    patch({
      step: "upload",
      project: undefined,
      surface: undefined,
      product: undefined,
      job: undefined,
    })

  const { project, product, job } = search
  const surface = isSurface(search.surface) ? search.surface : undefined

  let content: ReactNode
  if (step === "surface" && project) {
    content = (
      <SurfaceStep
        surface={surface}
        onSelect={(value) =>
          patch({ surface: value, product: undefined, job: undefined })
        }
        onBack={() => patch({ step: "upload" })}
        onNext={() => patch({ step: "product" })}
      />
    )
  } else if (step === "product" && project && surface) {
    content = (
      <ProductStep
        surface={surface}
        selectedProductId={product}
        onSelect={(value) => patch({ product: value, job: undefined })}
        onBack={() => patch({ step: "surface" })}
        onNext={() => patch({ step: "review" })}
      />
    )
  } else if (step === "review" && project && surface && product) {
    content = (
      <ReviewStep
        projectId={project}
        surface={surface}
        productId={product}
        isGenerating={generateMutation.isPending}
        onBack={() => patch({ step: "product" })}
        onGenerate={() =>
          generateMutation.mutate({
            projectId: project,
            productId: product,
            surface,
          })
        }
      />
    )
  } else if (step === "generate" && job) {
    content = (
      <GenerateStep jobId={job} onFinished={() => patch({ step: "result" })} />
    )
  } else if (step === "result" && project && surface && product && job) {
    content = (
      <ResultStep
        projectId={project}
        productId={product}
        surface={surface}
        jobId={job}
        isRetrying={retryMutation.isPending}
        onRetry={() => retryMutation.mutate(job)}
        onStartNew={startNew}
      />
    )
  } else {
    content = (
      <RoomPhotoStep
        onUploaded={(projectId) =>
          patch({
            step: "surface",
            project: projectId,
            surface: undefined,
            product: undefined,
            job: undefined,
          })
        }
      />
    )
  }

  return (
    <div className="flex flex-col gap-6" data-testid="visualizer-page">
      <div>
        <h1 className="text-headline-small text-on-surface">
          {t("visualizer.title")}
        </h1>
        <p className="mt-1 text-body-medium text-on-surface-variant">
          {t("visualizer.subtitle")}
        </p>
      </div>
      <VisualizerStepper current={step} />
      {content}
    </div>
  )
}
