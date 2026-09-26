import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  type OnChangeFn,
  type RowSelectionState,
  useReactTable,
} from "@tanstack/react-table"
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useLanguage } from "@/i18n/useLanguage"

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
  /** Enables TanStack row selection; add a selection column to use it. */
  enableRowSelection?: boolean
  /** Per-row guard so some rows cannot be selected. */
  isRowSelectable?: (row: TData) => boolean
  /** Stable row id. Required when using selection. */
  getRowId?: (row: TData) => string
  /** Controlled selection state. */
  rowSelection?: RowSelectionState
  onRowSelectionChange?: OnChangeFn<RowSelectionState>
}

export function DataTable<TData, TValue>({
  columns,
  data,
  enableRowSelection,
  isRowSelectable,
  getRowId,
  rowSelection,
  onRowSelectionChange,
}: DataTableProps<TData, TValue>) {
  const { t } = useTranslation()
  const { language } = useLanguage()
  const [internalRowSelection, setInternalRowSelection] =
    useState<RowSelectionState>({})
  const selectionState = rowSelection ?? internalRowSelection
  const selectionChange = onRowSelectionChange ?? setInternalRowSelection
  const formatNumber = (value: number) =>
    new Intl.NumberFormat(language).format(value)
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    enableRowSelection: isRowSelectable
      ? (row) => isRowSelectable(row.original)
      : enableRowSelection,
    getRowId: getRowId ? (row) => getRowId(row) : undefined,
    state: { rowSelection: selectionState },
    onRowSelectionChange: selectionChange,
  })

  const { pageIndex, pageSize } = table.getState().pagination
  const from = pageIndex * pageSize + 1
  const to = Math.min((pageIndex + 1) * pageSize, data.length)

  return (
    <div className="flex flex-col gap-4">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id} className="hover:bg-transparent">
              {headerGroup.headers.map((header) => {
                return (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                  </TableHead>
                )
              })}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.length ? (
            table.getRowModel().rows.map((row) => (
              <TableRow key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableRow className="hover:bg-transparent">
              <TableCell
                colSpan={columns.length}
                className="h-32 text-center text-muted-foreground"
              >
                {t("common.noResults")}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      {table.getPageCount() > 1 && (
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 border-t bg-muted/20">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <div className="text-sm text-muted-foreground">
              {t("common.showingEntries", {
                from: formatNumber(from),
                to: formatNumber(to),
                total: formatNumber(data.length),
              })}
            </div>
            <div className="flex items-center gap-x-2">
              <p className="text-sm text-muted-foreground">
                {t("common.rowsPerPage")}
              </p>
              <Select
                value={`${pageSize}`}
                onValueChange={(value) => {
                  table.setPageSize(Number(value))
                }}
              >
                <SelectTrigger className="h-8 w-[70px]">
                  <SelectValue placeholder={pageSize} />
                </SelectTrigger>
                <SelectContent side="top">
                  {[5, 10, 25, 50].map((size) => (
                    <SelectItem key={size} value={`${size}`}>
                      {formatNumber(size)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex items-center gap-x-6">
            <div className="flex items-center gap-x-1 text-sm text-muted-foreground">
              {t("common.pageOf", {
                page: formatNumber(pageIndex + 1),
                pages: formatNumber(table.getPageCount()),
              })}
            </div>

            <div className="flex items-center gap-x-1">
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => table.setPageIndex(0)}
                disabled={!table.getCanPreviousPage()}
              >
                <span className="sr-only">{t("navigation.goToFirstPage")}</span>
                <ChevronsLeft className="h-4 w-4 rtl:rotate-180" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
              >
                <span className="sr-only">
                  {t("navigation.goToPreviousPage")}
                </span>
                <ChevronLeft className="h-4 w-4 rtl:rotate-180" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
              >
                <span className="sr-only">{t("navigation.goToNextPage")}</span>
                <ChevronRight className="h-4 w-4 rtl:rotate-180" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => table.setPageIndex(table.getPageCount() - 1)}
                disabled={!table.getCanNextPage()}
              >
                <span className="sr-only">{t("navigation.goToLastPage")}</span>
                <ChevronsRight className="h-4 w-4 rtl:rotate-180" />
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
