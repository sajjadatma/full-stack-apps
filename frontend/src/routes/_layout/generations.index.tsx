import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { LoaderCircle } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"

import { GenerationsService } from "@/client"
import { GenerationHistoryCard } from "@/components/Generations/GenerationHistoryCard"
import { Button } from "@/components/ui/button"
import i18n from "@/i18n"

const PAGE_SIZE = 20

export const Route = createFileRoute("/_layout/generations/")({
  component: GenerationHistoryPage,
  head: () => ({ meta: [{ title: i18n.t("meta.generations") }] }),
})

function GenerationHistoryPage() {
  const { t } = useTranslation()
  const [page, setPage] = useState(0)
  const query = useQuery({
    queryKey: ["generation-history", page],
    queryFn: async () =>
      (
        await GenerationsService.readGenerations({
          query: { skip: page * PAGE_SIZE, limit: PAGE_SIZE },
        })
      ).data,
    retry: false,
  })

  if (query.isPending) {
    return (
      <div className="grid min-h-64 place-items-center" role="status">
        <LoaderCircle className="size-8 animate-spin text-primary" />
        <span className="sr-only">{t("generations.loading")}</span>
      </div>
    )
  }
  if (query.isError) {
    return (
      <section
        className="grid gap-4 rounded-xl border border-error p-6 text-on-surface"
        role="alert"
      >
        <h1 className="text-headline-small">{t("generations.errorTitle")}</h1>
        <p>{t("generations.errorDescription")}</p>
        <Button type="button" onClick={() => void query.refetch()}>
          {t("products.retry")}
        </Button>
      </section>
    )
  }

  const jobs = query.data.data
  const pageCount = Math.ceil(query.data.count / PAGE_SIZE)
  return (
    <section
      className="flex flex-col gap-6"
      data-testid="generation-history-page"
    >
      <header>
        <h1 className="text-headline-small text-on-surface">
          {t("generations.title")}
        </h1>
        <p className="mt-1 text-body-medium text-on-surface-variant">
          {t("generations.description")}
        </p>
      </header>
      {jobs.length === 0 ? (
        <div className="grid min-h-64 place-items-center rounded-xl border border-outline-variant p-8 text-center">
          <div>
            <h2 className="text-title-large">{t("generations.emptyTitle")}</h2>
            <p className="mt-2 text-body-medium text-on-surface-variant">
              {t("generations.emptyDescription")}
            </p>
          </div>
        </div>
      ) : (
        <div className="grid gap-4">
          {jobs.map((job) => (
            <GenerationHistoryCard key={job.id} job={job} />
          ))}
        </div>
      )}
      {pageCount > 1 && (
        <nav
          className="flex items-center justify-center gap-4"
          aria-label={t("generations.paginationLabel")}
        >
          <Button
            type="button"
            variant="outline"
            disabled={page === 0}
            onClick={() => setPage((value) => value - 1)}
          >
            {t("generations.previous")}
          </Button>
          <span aria-live="polite">
            {t("generations.page", { current: page + 1, total: pageCount })}
          </span>
          <Button
            type="button"
            variant="outline"
            disabled={page + 1 >= pageCount}
            onClick={() => setPage((value) => value + 1)}
          >
            {t("generations.next")}
          </Button>
        </nav>
      )}
    </section>
  )
}
