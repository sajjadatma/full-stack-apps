import { useQuery } from "@tanstack/react-query"

import { GenerationsService } from "@/client"

export function isTerminalStatus(status: string | undefined): boolean {
  return status === "COMPLETED" || status === "FAILED"
}

/**
 * Read and poll one generation job. Polling stops as soon as the job reaches a
 * terminal status. Never creates a job.
 */
export function useGenerationJob(jobId?: string) {
  return useQuery({
    queryKey: ["generation", jobId],
    queryFn: async () =>
      (await GenerationsService.readGeneration({ path: { job_id: jobId! } }))
        .data,
    enabled: Boolean(jobId),
    refetchInterval: (query) =>
      isTerminalStatus(query.state.data?.status) ? false : 1500,
  })
}
