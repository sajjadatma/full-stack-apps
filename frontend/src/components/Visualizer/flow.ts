import { z } from "zod"

/**
 * The six-step visualizer flow. Only stable identifiers live in the URL; image
 * bytes and object URLs stay in component state.
 */
export const visualizerSteps = [
  "upload",
  "surface",
  "product",
  "review",
  "generate",
  "result",
] as const

export type VisualizerStep = (typeof visualizerSteps)[number]

export type VisualizerSurface = "FLOOR" | "WALL"

export const visualizerSearchSchema = z.object({
  step: z.enum(visualizerSteps).optional().catch(undefined),
  project: z.uuid().optional().catch(undefined),
  surface: z.enum(["FLOOR", "WALL"]).optional().catch(undefined),
  product: z.uuid().optional().catch(undefined),
  job: z.uuid().optional().catch(undefined),
})

export type VisualizerSearch = z.infer<typeof visualizerSearchSchema>

export const stepIndex: Record<VisualizerStep, number> = {
  upload: 0,
  surface: 1,
  product: 2,
  review: 3,
  generate: 4,
  result: 5,
}

const indexStep: VisualizerStep[] = [
  "upload",
  "surface",
  "product",
  "review",
  "generate",
  "result",
]

/**
 * Highest step index reachable from the persisted identifiers. A job implies the
 * whole chain is available, so it unlocks both the generate and result steps.
 */
export function maxReachableIndex(search: VisualizerSearch): number {
  if (search.job) {
    return stepIndex.result
  }
  if (search.product && search.surface && search.project) {
    return stepIndex.review
  }
  if (search.surface && search.project) {
    return stepIndex.product
  }
  if (search.project) {
    return stepIndex.surface
  }
  return stepIndex.upload
}

export function stepForIndex(index: number): VisualizerStep {
  return indexStep[Math.max(0, Math.min(index, indexStep.length - 1))]
}

/** The earliest step at which the user can act, given the persisted state. */
export function resumeStep(search: VisualizerSearch): VisualizerStep {
  return stepForIndex(maxReachableIndex(search))
}

/**
 * Resolve the effective step for the current URL. A requested step beyond the
 * reachable state is clamped to the earliest valid step.
 */
export function resolveStep(search: VisualizerSearch): VisualizerStep {
  const requested = search.step ?? resumeStep(search)
  const requestedIndex = stepIndex[requested]
  const allowed = maxReachableIndex(search)
  return requestedIndex <= allowed ? requested : stepForIndex(allowed)
}

export function isSurface(
  value: string | undefined,
): value is VisualizerSurface {
  return value === "FLOOR" || value === "WALL"
}
