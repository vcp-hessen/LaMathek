<script setup lang="ts">
import { type ColumnDef } from '@tanstack/vue-table'
import { computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import type { MaterialType } from '../../schemas/material'
import DataTableFooter from '../data-table/DataTableFooter.vue'
import { localeSortRow } from '../data-table/localeSort'
import SortHeaderButton from '../data-table/SortHeaderButton.vue'
import { useClientTable } from '../data-table/useClientTable'
import PhotoThumbnail from '../PhotoThumbnail.vue'
import {
  buildVariantAxisCatalog,
  pruneVariantFilterToCatalog,
  variantFiltersAreActive,
} from '../../utils/pieceVariantFilters'
import { variantMapSummary } from '../../utils/variantDisplay'
import AddToBoxButton from '../loans/AddToBoxButton.vue'
import PiecesActiveFilterChips from '../pieces/PiecesActiveFilterChips.vue'
import PiecesTableToolbar from '../pieces/PiecesTableToolbar.vue'
import {
  type MaterialRow,
  createMaterialGlobalFilterFn,
  createMaterialTypeFilterFn,
  createMaterialVariantColumnFilterFn,
  rowCoverPhotoId,
  rowDisplayName,
  rowItemStatus,
  rowMaterialTypeName,
  type MaterialStatusFilter,
  type VariantColumnFilterValue,
} from './materialTableSetup'

const props = defineProps<{
  inventoryId: number
  rows: MaterialRow[]
  materialTypes: MaterialType[]
  statusFilter: MaterialStatusFilter
}>()

const emit = defineEmits<{
  'update:statusFilter': [value: MaterialStatusFilter]
}>()

const { t } = useI18n()
const router = useRouter()

const unlabeledLotLabel = computed(() => t('material.stockLotUnlabeled'))

const materialTypeById = computed(() => {
  const map = new Map<number, MaterialType>()
  for (const mt of props.materialTypes) map.set(mt.id, mt)
  return map
})

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

const {
  table,
  globalFilter,
  pagination,
  tableRows,
  filteredCount,
  pageCount,
  currentPage,
  pageFrom,
  pageTo,
  goToPage,
  setPageSize,
} = useClientTable<MaterialRow>({
  data: () => props.rows,
  columns,
  getRowId: (row) => row.id,
  globalFilterFn: () => createMaterialGlobalFilterFn(props.materialTypes, unlabeledLotLabel.value),
  initialSorting: [{ id: 'name', desc: false }],
  autoResetPageIndex: true,
})

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
    props.statusFilter !== 'active' ||
    !!materialTypeFilter.value ||
    variantFiltersAreActive(variantFilterValue.value),
)

function showRetiredBadge(row: MaterialRow): boolean {
  return (
    props.statusFilter !== 'active' && rowItemStatus(row) === 'retired'
  )
}

function showLostBadge(row: MaterialRow): boolean {
  return row.kind === 'piece' && row.piece.lost === true
}

watch(materialTypeFilter, () => {
  const pruned = pruneVariantFilterToCatalog(variantFilterValue.value, variantAxisCatalog.value)
  if (JSON.stringify(pruned) !== JSON.stringify(variantFilterValue.value)) {
    variantFilterValue.value = pruned
  }
})

function sortedState(columnId: string): false | 'asc' | 'desc' {
  return table.getColumn(columnId)?.getIsSorted() ?? false
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
  emit('update:statusFilter', 'active')
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
      :status-filter="statusFilter"
      :piece-types="materialTypes"
      :variant-catalog="variantAxisCatalog"
      :variant-filter="variantFilterValue"
      :has-active-filter="hasActiveFilter"
      @update:search-query="globalFilter = $event"
      @update:status-filter="emit('update:statusFilter', $event)"
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
      <table class="table table-sm data-table">
        <thead>
          <tr>
            <th class="data-table-col-photo hidden sm:table-cell">
              <span class="sr-only">{{ t('material.piecesTablePhoto') }}</span>
            </th>
            <th class="data-table-col-lead">
              <SortHeaderButton
                :label="t('material.piecesTableName')"
                :sorted="sortedState('name')"
                @toggle="table.getColumn('name')?.toggleSorting()"
              />
            </th>
            <th class="hidden md:table-cell">
              <SortHeaderButton
                :label="t('material.piecesTableMaterialType')"
                :sorted="sortedState('materialTypeName')"
                @toggle="table.getColumn('materialTypeName')?.toggleSorting()"
              />
            </th>
            <th class="hidden lg:table-cell">
              <SortHeaderButton
                :label="t('material.piecesTableVariant')"
                :sorted="sortedState('variant')"
                @toggle="table.getColumn('variant')?.toggleSorting()"
              />
            </th>
            <th class="hidden sm:table-cell">
              <SortHeaderButton
                :label="t('material.tableQuantity')"
                :sorted="sortedState('quantity')"
                @toggle="table.getColumn('quantity')?.toggleSorting()"
              />
            </th>
            <th class="hidden xl:table-cell">
              <SortHeaderButton
                :label="t('material.piecesTableSet')"
                :sorted="sortedState('set')"
                @toggle="table.getColumn('set')?.toggleSorting()"
              />
            </th>
            <th class="w-0">
              <span class="sr-only">{{ t('loans.addToBox') }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <template v-if="tableRows.length === 0">
            <tr>
              <td colspan="7" class="py-8 text-center text-sm opacity-70">
                {{ t('material.piecesNoSearchResults') }}
              </td>
            </tr>
          </template>
          <tr
            v-for="(row, index) in tableRows"
            v-else
            :key="row.id"
            tabindex="0"
            role="link"
            class="data-table-row cursor-pointer"
            :class="{ 'data-table-row--stripe': index % 2 === 1 }"
            @click="onRowClick(row.original)"
            @keydown="onRowKeydown($event, row.original)"
          >
            <td class="data-table-col-photo hidden sm:table-cell">
              <PhotoThumbnail :photo-id="rowCoverPhotoId(row.original)" />
            </td>
            <td class="data-table-col-lead min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <span class="font-medium">
                  {{ rowDisplayName(row.original, unlabeledLotLabel) }}
                </span>
                <span
                  v-if="showRetiredBadge(row.original)"
                  class="badge badge-ghost badge-sm"
                >
                  {{ t('material.itemStatusRetired') }}
                </span>
                <span
                  v-if="showLostBadge(row.original)"
                  class="badge badge-error badge-sm"
                >
                  {{ t('material.pieceLost') }}
                </span>
              </div>
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
            <td class="text-right" @click.stop>
              <AddToBoxButton
                v-if="row.original.kind === 'piece'"
                :inventory-id="inventoryId"
                :piece-id="row.original.piece.id"
                size="xs"
                :show-label="false"
              />
              <AddToBoxButton
                v-else
                :inventory-id="inventoryId"
                :material-type-id="row.original.lot.materialTypeId"
                :quantity="1"
                size="xs"
                :show-label="false"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <DataTableFooter
      :page-from="pageFrom"
      :page-to="pageTo"
      :total="filteredCount"
      :current-page="currentPage"
      :page-count="pageCount"
      :page-size="pagination.pageSize"
      @update:page-size="setPageSize"
      @go-to-page="goToPage"
    />
  </div>
</template>
