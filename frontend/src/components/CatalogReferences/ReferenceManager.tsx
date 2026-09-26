import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Pencil, Plus, RotateCcw, Trash2 } from "lucide-react"
import type { FormEvent } from "react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"

import {
  type BrandCreate,
  type BrandPublic,
  BrandsService,
  type BrandUpdate,
  CategoriesService,
  type CategoryCreate,
  type CategoryPublic,
  type CategoryUpdate,
} from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import useCustomToast from "@/hooks/useCustomToast"
import { useLanguage } from "@/i18n/useLanguage"
import { handleError } from "@/utils"

type ReferenceKind = "category" | "brand"
type Reference = CategoryPublic | BrandPublic
type FormValues = { name: string; slug: string; description: string }
type MutationInput =
  | { action: "create"; values: FormValues }
  | { action: "update"; id: string; values: FormValues }
  | { action: "status"; id: string; is_active: boolean }
  | { action: "delete"; id: string }

const blankForm: FormValues = { name: "", slug: "", description: "" }
const API_PAGE_SIZE = 100
const TABLE_PAGE_SIZE = 20

interface ReferenceManagerProps {
  kind: ReferenceKind
  canCreate: boolean
  canUpdate: boolean
  canDelete: boolean
}

export function ReferenceManager({
  kind,
  canCreate,
  canUpdate,
  canDelete,
}: ReferenceManagerProps) {
  const { t } = useTranslation()
  const { language } = useLanguage()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const isCategory = kind === "category"
  const label = t(
    isCategory ? "catalogReferences.category" : "catalogReferences.brand",
  )
  const queryKey = ["catalogReferences", kind]
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(0)
  const [formOpen, setFormOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [editing, setEditing] = useState<Reference | null>(null)
  const [deleting, setDeleting] = useState<Reference | null>(null)
  const [form, setForm] = useState<FormValues>(blankForm)

  const query = useQuery({
    queryKey,
    queryFn: async () => {
      const readPage = async (skip: number) =>
        isCategory
          ? (
              await CategoriesService.readCategories({
                query: { skip, limit: API_PAGE_SIZE },
              })
            ).data
          : (
              await BrandsService.readBrands({
                query: { skip, limit: API_PAGE_SIZE },
              })
            ).data
      // The categories/brands endpoints page with skip/limit and no search
      // parameter, so load every page up front and search/paginate in memory.
      const data: Reference[] = []
      let count = 0
      for (;;) {
        const page = await readPage(data.length)
        count = page.count
        data.push(...page.data)
        if (page.data.length === 0 || data.length >= page.count) break
      }
      return { count, data }
    },
  })

  const mutation = useMutation({
    mutationFn: async (input: MutationInput) => {
      if (input.action === "create") {
        const body = {
          ...input.values,
          description: input.values.description.trim() || null,
        }
        return isCategory
          ? CategoriesService.createCategory({
              body: body satisfies CategoryCreate,
            })
          : BrandsService.createBrand({ body: body satisfies BrandCreate })
      }
      if (input.action === "update") {
        const body = {
          ...input.values,
          description: input.values.description.trim() || null,
        }
        return isCategory
          ? CategoriesService.updateCategory({
              path: { category_id: input.id },
              body: body satisfies CategoryUpdate,
            })
          : BrandsService.updateBrand({
              path: { brand_id: input.id },
              body: body satisfies BrandUpdate,
            })
      }
      if (input.action === "status") {
        return isCategory
          ? CategoriesService.updateCategory({
              path: { category_id: input.id },
              body: { is_active: input.is_active },
            })
          : BrandsService.updateBrand({
              path: { brand_id: input.id },
              body: { is_active: input.is_active },
            })
      }
      return isCategory
        ? CategoriesService.deleteCategory({ path: { category_id: input.id } })
        : BrandsService.deleteBrand({ path: { brand_id: input.id } })
    },
    onSuccess: (_result, input) => {
      if (input.action === "delete") {
        showSuccessToast(
          t(
            isCategory
              ? "catalogReferences.categoryDeleted"
              : "catalogReferences.brandDeleted",
          ),
        )
        setDeleteOpen(false)
        setDeleting(null)
        setPage(0)
      } else if (input.action === "status") {
        showSuccessToast(
          t(
            input.is_active
              ? "catalogReferences.reactivatedSuccess"
              : "catalogReferences.deactivatedSuccess",
            { name: label },
          ),
        )
      } else {
        showSuccessToast(
          t(
            input.action === "create"
              ? isCategory
                ? "catalogReferences.categoryCreated"
                : "catalogReferences.brandCreated"
              : isCategory
                ? "catalogReferences.categoryUpdated"
                : "catalogReferences.brandUpdated",
          ),
        )
        setFormOpen(false)
        setEditing(null)
        setForm(blankForm)
      }
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ["catalogReferences"] })
      void queryClient.invalidateQueries({
        queryKey: [isCategory ? "categories" : "brands"],
      })
    },
  })

  useEffect(() => {
    if (!formOpen) return
    setForm(
      editing
        ? {
            name: editing.name,
            slug: editing.slug,
            description: editing.description ?? "",
          }
        : blankForm,
    )
  }, [editing, formOpen])

  const records = (query.data?.data ?? []).filter((record) => {
    const value = search.trim().toLocaleLowerCase(language)
    return (
      !value ||
      record.name.toLocaleLowerCase(language).includes(value) ||
      record.slug.toLocaleLowerCase(language).includes(value) ||
      (record.description ?? "").toLocaleLowerCase(language).includes(value)
    )
  })
  const pageCount = Math.max(1, Math.ceil(records.length / TABLE_PAGE_SIZE))
  const visibleRecords = records.slice(
    page * TABLE_PAGE_SIZE,
    (page + 1) * TABLE_PAGE_SIZE,
  )

  const openCreate = () => {
    setEditing(null)
    setForm(blankForm)
    setFormOpen(true)
  }

  const openEdit = (record: Reference) => {
    setEditing(record)
    setForm({
      name: record.name,
      slug: record.slug,
      description: record.description ?? "",
    })
    setFormOpen(true)
  }

  const submitForm = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    mutation.mutate({
      action: editing ? "update" : "create",
      ...(editing ? { id: editing.id } : {}),
      values: form,
    } as MutationInput)
  }

  const changeStatus = (record: Reference) =>
    mutation.mutate({
      action: "status",
      id: record.id,
      is_active: !record.is_active,
    })

  return (
    <section className="flex flex-col gap-4" aria-label={label}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-title-large text-on-surface">{label}</h2>
          <p className="text-body-medium text-on-surface-variant">
            {t("catalogReferences.recordCount", {
              count: query.data?.count ?? 0,
            })}
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input
            aria-label={t("catalogReferences.search", { name: label })}
            placeholder={t("catalogReferences.search", { name: label })}
            value={search}
            onChange={(event) => {
              setSearch(event.target.value)
              setPage(0)
            }}
            className="sm:w-64"
          />
          {canCreate && (
            <Button onClick={openCreate}>
              <Plus className="me-2 size-4" />
              {t("catalogReferences.add", { name: label })}
            </Button>
          )}
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-outline-variant bg-surface-container-low shadow-elevation-1">
        {query.isPending ? (
          <div
            className="grid min-h-48 place-items-center text-body-medium text-on-surface-variant"
            role="status"
          >
            {t("catalogReferences.loading", { name: label })}
          </div>
        ) : query.isError ? (
          <div
            className="grid min-h-48 place-items-center gap-3 p-6 text-center"
            role="alert"
          >
            <p className="text-body-medium text-on-surface">
              {t("catalogReferences.loadError", { name: label })}
            </p>
            <Button variant="outline" onClick={() => void query.refetch()}>
              {t("catalogReferences.retry")}
            </Button>
          </div>
        ) : records.length === 0 ? (
          <div className="grid min-h-48 place-items-center p-6 text-center">
            <div className="flex max-w-sm flex-col items-center gap-2">
              <p className="text-title-medium text-on-surface">
                {search
                  ? t("catalogReferences.noMatches")
                  : t("catalogReferences.empty", { name: label })}
              </p>
              <p className="text-body-medium text-on-surface-variant">
                {search
                  ? t("catalogReferences.noMatchesDescription")
                  : t("catalogReferences.emptyDescription", { name: label })}
              </p>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-surface-container-high hover:bg-surface-container-high">
                  <TableHead>{t("catalogReferences.name")}</TableHead>
                  <TableHead>{t("catalogReferences.slug")}</TableHead>
                  <TableHead>{t("catalogReferences.description")}</TableHead>
                  <TableHead>{t("catalogReferences.status")}</TableHead>
                  {(canUpdate || canDelete) && (
                    <TableHead>{t("common.actions")}</TableHead>
                  )}
                </TableRow>
              </TableHeader>
              <TableBody>
                {visibleRecords.map((record) => (
                  <TableRow key={record.id}>
                    <TableCell className="font-medium text-on-surface">
                      {record.name}
                    </TableCell>
                    <TableCell className="font-mono text-label-medium text-on-surface-variant">
                      {record.slug}
                    </TableCell>
                    <TableCell className="max-w-sm text-on-surface-variant">
                      {record.description || t("common.na")}
                    </TableCell>
                    <TableCell>
                      <Badge variant={record.is_active ? "default" : "outline"}>
                        {t(
                          record.is_active
                            ? "catalogReferences.active"
                            : "catalogReferences.inactive",
                        )}
                      </Badge>
                    </TableCell>
                    {(canUpdate || canDelete) && (
                      <TableCell>
                        <div className="flex flex-wrap items-center gap-2">
                          {canUpdate && (
                            <>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => openEdit(record)}
                              >
                                <Pencil className="me-1.5 size-4" />
                                {t("common.edit")}
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                disabled={mutation.isPending}
                                onClick={() => changeStatus(record)}
                              >
                                {record.is_active ? (
                                  t("catalogReferences.deactivate")
                                ) : (
                                  <>
                                    <RotateCcw className="me-1.5 size-4" />
                                    {t("catalogReferences.reactivate")}
                                  </>
                                )}
                              </Button>
                            </>
                          )}
                          {canDelete && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-destructive hover:text-destructive"
                              onClick={() => {
                                setDeleting(record)
                                setDeleteOpen(true)
                              }}
                            >
                              <Trash2 className="me-1.5 size-4" />
                              {t("common.delete")}
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
      {records.length > TABLE_PAGE_SIZE && (
        <div className="flex items-center justify-between gap-3">
          <span className="text-body-small text-on-surface-variant">
            {t("catalogReferences.pageSummary", {
              from: page * TABLE_PAGE_SIZE + 1,
              to: Math.min((page + 1) * TABLE_PAGE_SIZE, records.length),
              total: records.length,
            })}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 0}
              onClick={() => setPage((current) => Math.max(0, current - 1))}
            >
              {t("pagination.previous")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page + 1 >= pageCount}
              onClick={() => setPage((current) => current + 1)}
            >
              {t("pagination.next")}
            </Button>
          </div>
        </div>
      )}

      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {t(editing ? "catalogReferences.edit" : "catalogReferences.add", {
                name: label,
              })}
            </DialogTitle>
            <DialogDescription>
              {t("catalogReferences.formDescription", { name: label })}
            </DialogDescription>
          </DialogHeader>
          <form className="grid gap-4" onSubmit={submitForm}>
            <ReferenceInput
              label={t("catalogReferences.name")}
              value={form.name}
              onChange={(value) =>
                setForm((current) => ({ ...current, name: value }))
              }
              required
            />
            <ReferenceInput
              label={t("catalogReferences.slug")}
              value={form.slug}
              onChange={(value) =>
                setForm((current) => ({ ...current, slug: value }))
              }
              required
            />
            <label className="grid gap-1.5 text-label-large text-on-surface">
              <span>{t("catalogReferences.description")}</span>
              <textarea
                className="min-h-24 rounded-xs border border-outline bg-transparent px-4 py-3 text-body-medium outline-none focus-visible:border-primary focus-visible:ring-[3px] focus-visible:ring-primary/25"
                value={form.description}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    description: event.target.value,
                  }))
                }
              />
            </label>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setFormOpen(false)}
                disabled={mutation.isPending}
              >
                {t("common.cancel")}
              </Button>
              <Button type="submit" disabled={mutation.isPending}>
                {t("common.save")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {t("catalogReferences.delete", { name: label })}
            </DialogTitle>
            <DialogDescription>
              {t("catalogReferences.deleteDescription", {
                name: deleting?.name ?? "",
              })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setDeleteOpen(false)}
              disabled={mutation.isPending}
            >
              {t("common.cancel")}
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={mutation.isPending || !deleting}
              onClick={() =>
                deleting &&
                mutation.mutate({ action: "delete", id: deleting.id })
              }
            >
              {t("common.delete")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}

function ReferenceInput({
  label,
  value,
  onChange,
  required = false,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  required?: boolean
}) {
  const id = `reference-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`
  return (
    <div className="grid gap-1.5 text-label-large text-on-surface">
      <label htmlFor={id}>
        {label}
        {required && <span className="text-destructive"> *</span>}
      </label>
      <Input
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required={required}
      />
    </div>
  )
}
