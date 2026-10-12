import {
  type ColumnDef,
  type ColumnFiltersState,
  type FilterFn,
  type PaginationState,
  type SortingState,
  functionalUpdate,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useVueTable,
} from '@tanstack/vue-table'
import { computed, ref, toValue, watch, type MaybeRefOrGetter } from 'vue'
import { DATA_TABLE_PAGE_SIZE_OPTIONS } from './pageSize'

export function useClientTable<T>(options: {
  data: MaybeRefOrGetter<T[]>
  columns: MaybeRefOrGetter<ColumnDef<T>[]>
  getRowId?: (row: T) => string
  globalFilterFn?: () => FilterFn<T>
  initialSorting?: SortingState
  autoResetPageIndex?: boolean
}) {
  const globalFilter = ref('')
  const sorting = ref<SortingState>(options.initialSorting ?? [])
  const columnFilters = ref<ColumnFiltersState>([])
  const pagination = ref<PaginationState>({
    pageIndex: 0,
    pageSize: DATA_TABLE_PAGE_SIZE_OPTIONS[0],
  })

  const table = useVueTable({
    get data() {
      return toValue(options.data)
    },
    get columns() {
      return toValue(options.columns)
    },
    getRowId: options.getRowId,
    state: {
      get sorting() {
        return sorting.value
      },
      get columnFilters() {
        return columnFilters.value
      },
      get globalFilter() {
        return globalFilter.value
      },
      get pagination() {
        return pagination.value
      },
    },
    onSortingChange: (updater) => {
      sorting.value = functionalUpdate(updater, sorting.value)
    },
    onColumnFiltersChange: (updater) => {
      columnFilters.value = functionalUpdate(updater, columnFilters.value)
    },
    onGlobalFilterChange: (updater) => {
      globalFilter.value = functionalUpdate(updater, globalFilter.value)
    },
    onPaginationChange: (updater) => {
      pagination.value = functionalUpdate(updater, pagination.value)
    },
    globalFilterFn: (row, columnId, filterValue, addMeta) => {
      const fn = options.globalFilterFn?.()
      if (!fn) return true
      return fn(row, columnId, filterValue, addMeta)
    },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    autoResetPageIndex: options.autoResetPageIndex ?? false,
  })

  watch(globalFilter, () => table.setPageIndex(0))
  watch(columnFilters, () => table.setPageIndex(0), { deep: true })
  watch(
    () => pagination.value.pageSize,
    () => table.setPageIndex(0),
  )

  const tableRows = computed(() => table.getRowModel().rows)
  const filteredCount = computed(() => table.getFilteredRowModel().rows.length)
  const pageCount = computed(() => Math.max(1, table.getPageCount()))
  const currentPage = computed(() => pagination.value.pageIndex + 1)
  const pageFrom = computed(() =>
    filteredCount.value === 0 ? 0 : pagination.value.pageIndex * pagination.value.pageSize + 1,
  )
  const pageTo = computed(() =>
    Math.min((pagination.value.pageIndex + 1) * pagination.value.pageSize, filteredCount.value),
  )

  function goToPage(next: number) {
    table.setPageIndex(next - 1)
  }

  function setPageSize(size: number) {
    table.setPageSize(size)
  }

  return {
    table,
    globalFilter,
    sorting,
    columnFilters,
    pagination,
    tableRows,
    filteredCount,
    pageCount,
    currentPage,
    pageFrom,
    pageTo,
    goToPage,
    setPageSize,
  }
}
