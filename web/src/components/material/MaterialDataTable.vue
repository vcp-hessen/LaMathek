<script setup lang="ts">
import {
  type ColumnDef,
  type ColumnFiltersState,
  type PaginationState,
  type SortingState,
  functionalUpdate,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useVueTable,
} from '@tanstack/vue-table'
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  ChevronDownIcon,
  ChevronUpDownIcon,
  ChevronUpIcon,
} from '@heroicons/vue/24/outline'
import type { MaterialType } from '../../schemas/material'
import PhotoThumbnail from '../PhotoThumbnail.vue'
import {
  buildVariantAxisCatalog,
  pruneVariantFilterToCatalog,
  variantFiltersAreActive,
} from '../../utils/pieceVariantFilters'
import { variantMapSummary } from '../../utils/variantDisplay'
import PiecesActiveFilterChips from '../pieces/PiecesActiveFilterChips.vue'
import PiecesTableToolbar from '../pieces/PiecesTableToolbar.vue'
import {
  MATERIAL_PAGE_SIZE_OPTIONS,
  type MaterialRow,
  createMaterialGlobalFilterFn,
  createMaterialTypeFilterFn,
  createMaterialVariantColumnFilterFn,
  rowCoverPhotoId,
  rowDisplayName,
  rowMaterialTypeName,
  type VariantColumnFilterValue,
} from './materialTableSetup'

const props = defineProps<{
  inventoryId: number
  rows: MaterialRow[]
  materialTypes: MaterialType[]
}>()

const { t } = useI18n()
const router = useRouter()

const globalFilter = ref('')
const sorting = ref<SortingState>([{ id: 'name', desc: false }])
const columnFilters = ref<ColumnFiltersState>([])
const pagination = ref<PaginationState>({
  pageIndex: 0,
  pageSize: MATERIAL_PAGE_SIZE_OPTIONS[0],
})

const unlabeledLotLabel = computed(() => t('material.stockLotUnlabeled'))

const materialTypeById = computed(() => {
  const map = new Map<number, MaterialType>()
  for (const mt of props.materialTypes) map.set(mt.id, mt)
  return map
})

function localeSortRow(
  rowA: { getValue: (id: string) => unknown },
  rowB: { getValue: (id: string) => unknown },
  columnId: string,
) {
  return String(rowA.getValue(columnId)).localeCompare(String(rowB.getValue(columnId)), 'de')
}

function variantSortKey(row: MaterialRow): string {
  if (row.kind === 'piece') {
    const mt = props.materialTypes.find((r) => r.id === row.piece.materialTypeId)
    return mt ? variantMapSummary(mt.variants, row.piece.variant) : ''
  }
  return variantMapSummary(row.lot.variants, row.lot.variant)
}

function setSortKey(row: MaterialRow): string {
  if (row.kind !== 'piece') return ''
  const piece = row.piece
  if (!piece.setName) return ''
  if (piece.setRole === 'optional') {
    return `${piece.setName} (${t('sets.optionals')})`
  }
  if (piece.setRole === 'assignment') {
    return `${piece.setName} (${t('sets.assignment')})`
  }
  return piece.setName
}

function quantitySortKey(row: MaterialRow): string {
  if (row.kind === 'piece') return ''
  const lot = row.lot
  return `${lot.quantity}${lot.unit ? ` ${lot.unit}` : ''}`
}

const columns = computed<ColumnDef<MaterialRow>[]>(() => [
  {
    id: 'photo',
    enableSorting: false,
    enableColumnFilter: false,
  },
  {
    id: 'name',
    accessorFn: (row) => rowDisplayName(row, unlabeledLotLabel.value),
    enableSorting: true,
    sortingFn: localeSortRow,
  },
  {
    id: 'materialTypeName',
    accessorFn: (row) => rowMaterialTypeName(row),
    enableSorting: true,
    enableColumnFilter: true,
    filterFn: createMaterialTypeFilterFn(),
    sortingFn: localeSortRow,
  },
  {
    id: 'variant',
    accessorFn: (row) => variantSortKey(row),
    enableSorting: true,
    enableColumnFilter: true,
    filterFn: createMaterialVariantColumnFilterFn(materialTypeById.value),
    sortingFn: localeSortRow,
  },
  {
    id: 'quantity',
    accessorFn: (row) => quantitySortKey(row),
    enableSorting: true,
    sortingFn: localeSortRow,
  },
  {
    id: 'set',
    accessorFn: (row) => setSortKey(row),
    enableSorting: true,
    enableColumnFilter: false,
    sortingFn: localeSortRow,
  },
])

const table = useVueTable({
  get data() {
    return props.rows
  },
  get columns() {
    return columns.value
  },
  getRowId: (row) => row.id,
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
  globalFilterFn: (row, columnId, filterValue, addMeta) =>
    createMaterialGlobalFilterFn(props.materialTypes, unlabeledLotLabel.value)(
      row,
      columnId,
      filterValue,
      addMeta,
    ),
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel(),
  getFilteredRowModel: getFilteredRowModel(),
  getPaginationRowModel: getPaginationRowModel(),
  autoResetPageIndex: true,
})

watch(globalFilter, () => table.setPageIndex(0))
watch(columnFilters, () => table.setPageIndex(0), { deep: true })
watch(
  () => pagination.value.pageSize,
  () => table.setPageIndex(0),
)

const tableRows = computed(() => table.getRowModel().rows)
const filteredCount = computed(() => table.getFilteredRowModel().rows.length)

const materialTypeFilter = computed(() => {
  const value = table.getColumn('materialTypeName')?.getFilterValue()
  return value === undefined || value === null ? '' : String(value)
})

const variantAxisCatalog = computed(() => {
  if (materialTypeFilter.value) {
    const mt = props.materialTypes.find((row) => String(row.id) === materialTypeFilter.value)
    if (mt) return buildVariantAxisCatalog([mt])
  }
  return buildVariantAxisCatalog(props.materialTypes)
})

const variantFilterValue = computed({
  get(): VariantColumnFilterValue {
    const value = table.getColumn('variant')?.getFilterValue()
    if (value && typeof value === 'object') return value as VariantColumnFilterValue
    return {}
  },
  set(next: VariantColumnFilterValue) {
    table.getColumn('variant')?.setFilterValue(next)
  },
})

const hasActiveFilter = computed(
  () =>
    !!globalFilter.value.trim() ||
    !!materialTypeFilter.value ||
    variantFiltersAreActive(variantFilterValue.value),
)

watch(materialTypeFilter, () => {
  const pruned = pruneVariantFilterToCatalog(variantFilterValue.value, variantAxisCatalog.value)
  if (JSON.stringify(pruned) !== JSON.stringify(variantFilterValue.value)) {
    variantFilterValue.value = pruned
  }
})

const pageCount = computed(() => table.getPageCount())
const currentPage = computed(() => pagination.value.pageIndex + 1)
const pageFrom = computed(() =>
  filteredCount.value === 0 ? 0 : pagination.value.pageIndex * pagination.value.pageSize + 1,
)
const pageTo = computed(() =>
  Math.min((pagination.value.pageIndex + 1) * pagination.value.pageSize, filteredCount.value),
)

function sortIcon(columnId: 'name' | 'materialTypeName' | 'variant' | 'quantity' | 'set') {
  const sorted = table.getColumn(columnId)?.getIsSorted()
  if (sorted === 'asc') return ChevronUpIcon
  if (sorted === 'desc') return ChevronDownIcon
  return ChevronUpDownIcon
}

function setLabel(row: MaterialRow): string {
  const key = setSortKey(row)
  return key || '—'
}

function quantityLabel(row: MaterialRow): string {
  if (row.kind === 'piece') return '—'
  const lot = row.lot
  return `${lot.quantity}${lot.unit ? ` ${lot.unit}` : ''}`
}

function goToPiece(pieceId: number) {
  void router.push(`/inventories/${props.inventoryId}/pieces/${pieceId}`)
}

function goToStockLot(lotId: number) {
  void router.push(`/inventories/${props.inventoryId}/stock-lots/${lotId}`)
}

function setMaterialTypeFilter(value: string) {
  table.getColumn('materialTypeName')?.setFilterValue(value || undefined)
}

function resetAllFilters() {
  globalFilter.value = ''
  table.getColumn('materialTypeName')?.setFilterValue(undefined)
  table.getColumn('variant')?.setFilterValue({})
}

function removeVariantValue(label: string, value: string) {
  const current = variantFilterValue.value[label] ?? []
  const next = current.filter((v) => v !== value)
  const nextFilter = { ...variantFilterValue.value, [label]: next }
  if (next.length === 0) {
    const copy = { ...nextFilter }
    delete copy[label]
    variantFilterValue.value = copy
  } else {
    variantFilterValue.value = nextFilter
  }
}

function goToPage(next: number) {
  table.setPageIndex(next - 1)
}

function onRowClick(row: MaterialRow) {
  if (row.kind === 'piece') {
    goToPiece(row.piece.id)
    return
  }
  goToStockLot(row.lot.id)
}

function onRowKeydown(event: KeyboardEvent, row: MaterialRow) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    onRowClick(row)
  }
}
</script>

<template>
  <div class="rounded-lg border border-base-200">
    <PiecesTableToolbar
      :search-query="globalFilter"
      :material-type-id="materialTypeFilter"
      :piece-types="materialTypes"
      :variant-catalog="variantAxisCatalog"
      :variant-filter="variantFilterValue"
      :has-active-filter="hasActiveFilter"
      @update:search-query="globalFilter = $event"
      @update:material-type-id="setMaterialTypeFilter"
      @update:variant-filter="variantFilterValue = $event"
      @reset="resetAllFilters"
    />
    <PiecesActiveFilterChips
      :search-query="globalFilter"
      :material-type-id="materialTypeFilter"
      :piece-types="materialTypes"
      :variant-filter="variantFilterValue"
      @clear-search="globalFilter = ''"
      @clear-material-type="setMaterialTypeFilter('')"
      @remove-variant-value="removeVariantValue"
    />
    <div class="overflow-x-auto">
      <table class="table table-sm pieces-table">
        <thead>
          <tr>
            <th class="pieces-table-col-photo hidden sm:table-cell">
              <span class="sr-only">{{ t('material.piecesTablePhoto') }}</span>
            </th>
            <th class="pieces-table-col-lead">
              <button
                type="button"
                class="flex items-center gap-1 font-semibold hover:text-primary"
                @click="table.getColumn('name')?.toggleSorting()"
              >
                {{ t('material.piecesTableName') }}
                <component :is="sortIcon('name')" class="size-4 opacity-60" aria-hidden="true" />
              </button>
            </th>
            <th class="hidden md:table-cell">
              <button
                type="button"
                class="flex items-center gap-1 font-semibold hover:text-primary"
                @click="table.getColumn('materialTypeName')?.toggleSorting()"
              >
                {{ t('material.piecesTableMaterialType') }}
                <component
                  :is="sortIcon('materialTypeName')"
                  class="size-4 opacity-60"
                  aria-hidden="true"
                />
              </button>
            </th>
            <th class="hidden lg:table-cell">
              <button
                type="button"
                class="flex items-center gap-1 font-semibold hover:text-primary"
                @click="table.getColumn('variant')?.toggleSorting()"
              >
                {{ t('material.piecesTableVariant') }}
                <component
                  :is="sortIcon('variant')"
                  class="size-4 opacity-60"
                  aria-hidden="true"
                />
              </button>
            </th>
            <th class="hidden sm:table-cell">
              <button
                type="button"
                class="flex items-center gap-1 font-semibold hover:text-primary"
                @click="table.getColumn('quantity')?.toggleSorting()"
              >
                {{ t('material.tableQuantity') }}
                <component
                  :is="sortIcon('quantity')"
                  class="size-4 opacity-60"
                  aria-hidden="true"
                />
              </button>
            </th>
            <th class="hidden xl:table-cell">
              <button
                type="button"
                class="flex items-center gap-1 font-semibold hover:text-primary"
                @click="table.getColumn('set')?.toggleSorting()"
              >
                {{ t('material.piecesTableSet') }}
                <component :is="sortIcon('set')" class="size-4 opacity-60" aria-hidden="true" />
              </button>
            </th>
          </tr>
        </thead>
        <tbody>
          <template v-if="tableRows.length === 0">
            <tr>
              <td colspan="6" class="py-8 text-center text-sm opacity-70">
                {{ t('material.piecesNoSearchResults') }}
              </td>
            </tr>
          </template>
          <tr
            v-for="row in tableRows"
            v-else
            :key="row.id"
            tabindex="0"
            role="link"
            class="cursor-pointer hover:bg-base-200/40"
            @click="onRowClick(row.original)"
            @keydown="onRowKeydown($event, row.original)"
          >
            <td class="pieces-table-col-photo hidden sm:table-cell">
              <PhotoThumbnail :photo-id="rowCoverPhotoId(row.original)" />
            </td>
            <td class="pieces-table-col-lead min-w-0">
              <span class="font-medium">
                {{ rowDisplayName(row.original, unlabeledLotLabel) }}
              </span>
              <div class="mt-0.5 space-y-0.5 text-xs opacity-70">
                <span class="block md:hidden">{{ rowMaterialTypeName(row.original) }}</span>
                <span v-if="variantSortKey(row.original)" class="block lg:hidden">
                  {{ variantSortKey(row.original) }}
                </span>
                <span
                  v-if="row.original.kind === 'piece' && row.original.piece.setName"
                  class="block xl:hidden"
                >
                  {{ setLabel(row.original) }}
                </span>
                <span v-if="row.original.kind === 'stockLot'" class="block sm:hidden">
                  {{ quantityLabel(row.original) }}
                </span>
              </div>
            </td>
            <td class="hidden md:table-cell">{{ rowMaterialTypeName(row.original) }}</td>
            <td class="hidden max-w-[12rem] truncate lg:table-cell">
              {{ variantSortKey(row.original) || '—' }}
            </td>
            <td class="hidden sm:table-cell">{{ quantityLabel(row.original) }}</td>
            <td class="hidden max-w-[10rem] truncate xl:table-cell">
              {{ setLabel(row.original) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div
      class="flex flex-wrap items-center justify-between gap-3 border-t border-base-200 px-3 py-2.5"
    >
      <p class="text-xs opacity-70">
        {{
          t('material.piecesPageRange', {
            from: pageFrom,
            to: pageTo,
            total: filteredCount,
          })
        }}
        <span class="opacity-80">
          ·
          {{
            t('material.piecesPageOf', {
              current: currentPage,
              pages: pageCount,
            })
          }}
        </span>
      </p>
      <div class="flex flex-wrap items-center gap-2">
        <label class="flex items-center gap-2">
          <span class="text-xs opacity-80">{{ t('material.piecesPageSize') }}</span>
          <select
            :value="pagination.pageSize"
            class="select select-bordered select-sm w-20"
            @change="table.setPageSize(Number(($event.target as HTMLSelectElement).value))"
          >
            <option v-for="size in MATERIAL_PAGE_SIZE_OPTIONS" :key="size" :value="size">
              {{ size }}
            </option>
          </select>
        </label>
        <div class="join">
          <button
            type="button"
            class="btn btn-sm join-item"
            :disabled="currentPage <= 1"
            :aria-label="t('material.piecesPreviousPage')"
            @click="goToPage(currentPage - 1)"
          >
            ‹
          </button>
          <button
            type="button"
            class="btn btn-sm join-item"
            :disabled="currentPage >= pageCount"
            :aria-label="t('material.piecesNextPage')"
            @click="goToPage(currentPage + 1)"
          >
            ›
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
