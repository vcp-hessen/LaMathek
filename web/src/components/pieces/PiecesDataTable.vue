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
import type { MaterialType, Piece } from '../../schemas/material'
import PhotoThumbnail from '../PhotoThumbnail.vue'
import {
  buildVariantAxisCatalog,
  pruneVariantFilterToCatalog,
  variantFiltersAreActive,
} from '../../utils/pieceVariantFilters'
import { variantMapSummary } from '../../utils/variantDisplay'
import PiecesActiveFilterChips from './PiecesActiveFilterChips.vue'
import PiecesTableToolbar from './PiecesTableToolbar.vue'
import {
  PIECES_PAGE_SIZE_OPTIONS,
  createMaterialTypeFilterFn,
  createPieceGlobalFilterFn,
  createVariantColumnFilterFn,
  type VariantColumnFilterValue,
} from './piecesTableSetup'

const props = defineProps<{
  inventoryId: number
  pieces: Piece[]
  pieceTypes: MaterialType[]
  materialTypes: MaterialType[]
}>()

const { t } = useI18n()
const router = useRouter()

const globalFilter = ref('')
const sorting = ref<SortingState>([{ id: 'name', desc: false }])
const columnFilters = ref<ColumnFiltersState>([])
const pagination = ref<PaginationState>({
  pageIndex: 0,
  pageSize: PIECES_PAGE_SIZE_OPTIONS[0],
})

const materialTypeById = computed(() => {
  const map = new Map<number, MaterialType>()
  for (const mt of props.pieceTypes) map.set(mt.id, mt)
  return map
})

function localeSortRow(
  rowA: { getValue: (id: string) => unknown },
  rowB: { getValue: (id: string) => unknown },
  columnId: string,
) {
  return String(rowA.getValue(columnId)).localeCompare(String(rowB.getValue(columnId)), 'de')
}

function variantSortKey(piece: Piece): string {
  const mt = props.materialTypes.find((row) => row.id === piece.materialTypeId)
  return mt ? variantMapSummary(mt.variants, piece.variant) : ''
}

function setSortKey(piece: Piece): string {
  if (!piece.setName) return ''
  if (piece.setRole === 'optional') {
    return `${piece.setName} (${t('sets.optionals')})`
  }
  if (piece.setRole === 'assignment') {
    return `${piece.setName} (${t('sets.assignment')})`
  }
  return piece.setName
}

const columns = computed<ColumnDef<Piece>[]>(() => [
  {
    id: 'photo',
    enableSorting: false,
    enableColumnFilter: false,
  },
  {
    accessorKey: 'name',
    id: 'name',
    enableSorting: true,
    sortingFn: localeSortRow,
  },
  {
    accessorKey: 'materialTypeName',
    id: 'materialTypeName',
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
    filterFn: createVariantColumnFilterFn(materialTypeById.value),
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
    return props.pieces
  },
  get columns() {
    return columns.value
  },
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
    createPieceGlobalFilterFn(props.materialTypes)(row, columnId, filterValue, addMeta),
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

const rows = computed(() => table.getRowModel().rows)
const filteredCount = computed(() => table.getFilteredRowModel().rows.length)

const materialTypeFilter = computed(() => {
  const value = table.getColumn('materialTypeName')?.getFilterValue()
  return value === undefined || value === null ? '' : String(value)
})

const variantAxisCatalog = computed(() => {
  if (materialTypeFilter.value) {
    const mt = props.pieceTypes.find((row) => String(row.id) === materialTypeFilter.value)
    if (mt) return buildVariantAxisCatalog([mt])
  }
  return buildVariantAxisCatalog(props.pieceTypes)
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

function sortIcon(columnId: 'name' | 'materialTypeName' | 'variant' | 'set') {
  const sorted = table.getColumn(columnId)?.getIsSorted()
  if (sorted === 'asc') return ChevronUpIcon
  if (sorted === 'desc') return ChevronDownIcon
  return ChevronUpDownIcon
}

function pieceVariantSummary(piece: Piece): string {
  return variantSortKey(piece)
}

function setLabel(piece: Piece): string {
  const key = setSortKey(piece)
  return key || '—'
}

function goToPiece(pieceId: number) {
  void router.push(`/inventories/${props.inventoryId}/pieces/${pieceId}`)
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
</script>

<template>
  <div class="rounded-lg border border-base-200">
    <PiecesTableToolbar
      :search-query="globalFilter"
      :material-type-id="materialTypeFilter"
      :piece-types="pieceTypes"
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
      :piece-types="pieceTypes"
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
                @click="table.getColumn('set')?.toggleSorting()"
              >
                {{ t('material.piecesTableSet') }}
                <component :is="sortIcon('set')" class="size-4 opacity-60" aria-hidden="true" />
              </button>
            </th>
          </tr>
        </thead>
        <tbody>
          <template v-if="rows.length === 0">
            <tr>
              <td colspan="5" class="py-8 text-center text-sm opacity-70">
                {{ t('material.piecesNoSearchResults') }}
              </td>
            </tr>
          </template>
          <tr
            v-for="row in rows"
            v-else
            :key="row.id"
            tabindex="0"
            role="link"
            class="cursor-pointer"
            @click="goToPiece(row.original.id)"
            @keydown.enter.prevent="goToPiece(row.original.id)"
            @keydown.space.prevent="goToPiece(row.original.id)"
          >
            <td class="pieces-table-col-photo hidden sm:table-cell">
              <PhotoThumbnail :photo-id="row.original.coverPhotoId" />
            </td>
            <td class="pieces-table-col-lead min-w-0">
              <span class="font-medium">{{ row.original.name }}</span>
              <div class="mt-0.5 space-y-0.5 text-xs opacity-70">
                <span class="block md:hidden">{{ row.original.materialTypeName }}</span>
                <span v-if="pieceVariantSummary(row.original)" class="block lg:hidden">
                  {{ pieceVariantSummary(row.original) }}
                </span>
                <span v-if="row.original.setName" class="block sm:hidden">
                  {{ setLabel(row.original) }}
                </span>
              </div>
            </td>
            <td class="hidden md:table-cell">{{ row.original.materialTypeName }}</td>
            <td class="hidden max-w-[12rem] truncate lg:table-cell">
              {{ pieceVariantSummary(row.original) || '—' }}
            </td>
            <td class="hidden max-w-[10rem] truncate sm:table-cell">
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
            <option v-for="size in PIECES_PAGE_SIZE_OPTIONS" :key="size" :value="size">
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
