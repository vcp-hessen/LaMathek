<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import type { ColumnDef } from '@tanstack/vue-table'
import type { LoanLine } from '../../schemas/loan'
import DataTableSearch from '../data-table/DataTableSearch.vue'
import DataTableFooter from '../data-table/DataTableFooter.vue'
import SortHeaderButton from '../data-table/SortHeaderButton.vue'
import { useClientTable } from '../data-table/useClientTable'
import { localeSortRow } from '../data-table/localeSort'
import LoanLineRowActionsMenu from './LoanLineRowActionsMenu.vue'
import type { LineRowActionId } from './loanLineRowActions'
import type { LoanWorkflowContext } from '../../domain/loanWorkflowSteps'

const props = defineProps<{
  lines: LoanLine[]
  inventoryId: number
  selectedLineIds: number[]
  canManage: boolean
  isLoanBorrower: boolean
  canParticipate: boolean
  confirmAllowed: boolean
  confirmBlockedTitle: string
  workflow: LoanWorkflowContext
}>()

const emit = defineEmits<{
  toggleLine: [id: number, checked: boolean]
  selectLines: [ids: number[]]
  deselectLines: [ids: number[]]
  removeLine: [lineId: number]
  rowAction: [payload: { id: LineRowActionId; lineId: number }]
}>()

const { t } = useI18n()
const router = useRouter()

function lineDisplayName(line: LoanLine): string {
  if (line.kind === 'piece') return line.pieceName
  return line.materialTypeName
}

function lineMaterialTypeName(line: LoanLine): string {
  return line.materialTypeName
}

function lineQuantitySort(line: LoanLine): number {
  if (line.kind === 'stock') return line.quantity
  return -1
}

function lineQuantityLabel(line: LoanLine): string {
  if (line.kind === 'piece') return '—'
  return String(line.quantity)
}

function lineSetSort(line: LoanLine): string {
  return line.originSetName?.trim() ?? ''
}

function lineSetLabel(line: LoanLine): string {
  const key = lineSetSort(line)
  return key || '—'
}

function lineStatusLabel(status: string): string {
  const key = `loans.lineStatus_${status}` as const
  const translated = t(key)
  if (translated !== key) return translated
  return status
}

function lineStatusSort(line: LoanLine): string {
  return lineStatusLabel(line.status)
}

function optionalTag(line: LoanLine): boolean {
  return line.originSetRole === 'optional'
}

const headerCheckboxRef = ref<HTMLInputElement | null>(null)

const columns = computed<ColumnDef<LoanLine>[]>(() => [
  {
    id: 'name',
    accessorFn: (line) => lineDisplayName(line),
    enableSorting: true,
    sortingFn: localeSortRow,
  },
  {
    id: 'materialTypeName',
    accessorFn: (line) => lineMaterialTypeName(line),
    enableSorting: true,
    sortingFn: localeSortRow,
  },
  {
    id: 'quantity',
    accessorFn: (line) => lineQuantitySort(line),
    enableSorting: true,
    sortingFn: (rowA, rowB) =>
      lineQuantitySort(rowA.original) - lineQuantitySort(rowB.original),
  },
  {
    id: 'set',
    accessorFn: (line) => lineSetSort(line),
    enableSorting: true,
    sortingFn: localeSortRow,
  },
  {
    id: 'status',
    accessorFn: (line) => lineStatusSort(line),
    enableSorting: true,
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
} = useClientTable<LoanLine>({
  data: () => props.lines,
  columns,
  getRowId: (line) => String(line.id),
  globalFilterFn: () => (row, _columnId, filterValue) => {
    const q = String(filterValue).trim().toLowerCase()
    if (!q) return true
    const line = row.original
    const haystack = [
      lineDisplayName(line),
      lineMaterialTypeName(line),
      lineSetLabel(line),
      lineStatusLabel(line.status),
      line.reason,
      line.note,
    ]
      .join(' ')
      .toLowerCase()
    return haystack.includes(q)
  },
  initialSorting: [{ id: 'set', desc: false }, { id: 'name', desc: false }],
  autoResetPageIndex: true,
})

const filteredLineIds = computed(() =>
  table.getFilteredRowModel().rows.map((row) => row.original.id),
)

const allFilteredSelected = computed(
  () =>
    filteredLineIds.value.length > 0 &&
    filteredLineIds.value.every((id) => props.selectedLineIds.includes(id)),
)

const someFilteredSelected = computed(
  () =>
    filteredLineIds.value.some((id) => props.selectedLineIds.includes(id)) &&
    !allFilteredSelected.value,
)

watch(
  [someFilteredSelected, allFilteredSelected],
  () => {
    const el = headerCheckboxRef.value
    if (!el) return
    el.indeterminate = someFilteredSelected.value
  },
  { flush: 'post' },
)

function selectAllFiltered() {
  if (!filteredLineIds.value.length) return
  emit('selectLines', filteredLineIds.value)
}

function deselectFiltered() {
  if (!filteredLineIds.value.length) return
  emit('deselectLines', filteredLineIds.value)
}

function onHeaderCheckboxChange(event: Event) {
  const checked = (event.target as HTMLInputElement).checked
  if (checked) selectAllFiltered()
  else deselectFiltered()
}

function sortedState(columnId: string): false | 'asc' | 'desc' {
  return table.getColumn(columnId)?.getIsSorted() ?? false
}

function isSelected(lineId: number): boolean {
  return props.selectedLineIds.includes(lineId)
}

function toggleRow(line: LoanLine) {
  emit('toggleLine', line.id, !isSelected(line.id))
}

function rowKeydownIgnoresSelection(event: KeyboardEvent): boolean {
  const target = event.target
  if (!(target instanceof HTMLElement)) return false
  return Boolean(
    target.closest(
      'input, textarea, select, button, a, [contenteditable="true"], [role="menu"]',
    ),
  )
}

function onRowKeydown(event: KeyboardEvent, line: LoanLine) {
  if (rowKeydownIgnoresSelection(event)) return
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    toggleRow(line)
  }
}

function reasonDisplay(line: LoanLine): string {
  const parts: string[] = []
  if (line.reason.trim()) parts.push(line.reason.trim())
  if (line.note.trim()) parts.push(line.note.trim())
  return parts.join(' · ')
}

function openLineTarget(line: LoanLine, event: MouseEvent) {
  if (line.kind === 'piece') {
    event.stopPropagation()
    void router.push(`/inventories/${props.inventoryId}/pieces/${line.pieceId}`)
    return
  }
  if (line.kind === 'stock') {
    event.stopPropagation()
    void router.push(
      `/inventories/${props.inventoryId}/material?materialTypeId=${line.materialTypeId}`,
    )
  }
}
</script>

<template>
  <div class="rounded-lg border border-base-200">
    <div
      class="data-table-toolbar flex flex-col gap-3 border-b border-base-200 p-3 sm:flex-row sm:flex-wrap sm:items-end"
    >
      <DataTableSearch
        :model-value="globalFilter"
        :label="t('loans.searchLabel')"
        :placeholder="t('loans.linesSearchPlaceholder')"
        @update:model-value="globalFilter = $event"
      />
    </div>
    <div class="overflow-x-auto">
      <table class="table table-sm data-table">
        <thead>
          <tr>
            <th class="w-0">
              <input
                ref="headerCheckboxRef"
                type="checkbox"
                class="checkbox checkbox-sm"
                :checked="allFilteredSelected"
                :disabled="filteredLineIds.length === 0"
                :aria-label="t('loans.selectAllLines')"
                @change="onHeaderCheckboxChange"
              />
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
            <th class="hidden sm:table-cell">
              <SortHeaderButton
                :label="t('material.tableQuantity')"
                :sorted="sortedState('quantity')"
                @toggle="table.getColumn('quantity')?.toggleSorting()"
              />
            </th>
            <th class="hidden lg:table-cell">
              <SortHeaderButton
                :label="t('material.piecesTableSet')"
                :sorted="sortedState('set')"
                @toggle="table.getColumn('set')?.toggleSorting()"
              />
            </th>
            <th class="hidden sm:table-cell">
              <SortHeaderButton
                :label="t('loans.lineColumnStatus')"
                :sorted="sortedState('status')"
                @toggle="table.getColumn('status')?.toggleSorting()"
              />
            </th>
            <th class="hidden lg:table-cell min-w-[8rem]">
              <span class="text-xs font-semibold uppercase tracking-wide opacity-70">
                {{ t('loans.reason') }}
              </span>
            </th>
            <th class="w-0">
              <span class="sr-only">{{ t('loans.lineRowActionsMenu') }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="tableRows.length === 0">
            <td colspan="8" class="py-8 text-center text-sm opacity-70">
              {{ t('dataTable.noResults') }}
            </td>
          </tr>
          <tr
            v-for="(row, index) in tableRows"
            v-else
            :key="row.id"
            tabindex="0"
            class="data-table-row cursor-pointer"
            :class="{
              'data-table-row--stripe': index % 2 === 1,
              'bg-primary/10': isSelected(row.original.id),
            }"
            @click="toggleRow(row.original)"
            @keydown="onRowKeydown($event, row.original)"
          >
            <td @click.stop>
              <input
                type="checkbox"
                class="checkbox checkbox-sm"
                :checked="isSelected(row.original.id)"
                :aria-label="lineDisplayName(row.original)"
                @change="
                  emit(
                    'toggleLine',
                    row.original.id,
                    ($event.target as HTMLInputElement).checked,
                  )
                "
              />
            </td>
            <td class="data-table-col-lead min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  class="font-medium text-left hover:underline"
                  @click="openLineTarget(row.original, $event)"
                >
                  {{ lineDisplayName(row.original) }}
                </button>
                <span
                  v-if="optionalTag(row.original)"
                  class="badge badge-ghost badge-sm"
                >
                  {{ t('sets.optionals') }}
                </span>
              </div>
              <div class="mt-0.5 space-y-0.5 text-xs opacity-70">
                <span class="block md:hidden">{{ lineMaterialTypeName(row.original) }}</span>
                <span v-if="row.original.kind === 'stock'" class="block sm:hidden">
                  {{ t('material.tableQuantity') }}: {{ lineQuantityLabel(row.original) }}
                </span>
                <span
                  v-if="lineSetSort(row.original)"
                  class="block lg:hidden"
                >
                  {{ t('material.piecesTableSet') }}: {{ lineSetLabel(row.original) }}
                </span>
                <span class="block sm:hidden">{{ lineStatusLabel(row.original.status) }}</span>
                <span v-if="reasonDisplay(row.original)" class="block lg:hidden">
                  {{ reasonDisplay(row.original) }}
                </span>
              </div>
            </td>
            <td class="hidden md:table-cell">{{ lineMaterialTypeName(row.original) }}</td>
            <td class="hidden sm:table-cell tabular-nums">
              {{ lineQuantityLabel(row.original) }}
            </td>
            <td class="hidden max-w-[10rem] truncate lg:table-cell">
              {{ lineSetLabel(row.original) }}
            </td>
            <td class="hidden sm:table-cell">{{ lineStatusLabel(row.original.status) }}</td>
            <td class="hidden lg:table-cell min-w-[8rem] max-w-[14rem]">
              <span class="block truncate text-xs opacity-80">
                {{ reasonDisplay(row.original) || '—' }}
              </span>
            </td>
            <td class="text-right" @click.stop>
              <LoanLineRowActionsMenu
                :line="row.original"
                :can-manage="canManage"
                :is-loan-borrower="isLoanBorrower"
                :can-participate="canParticipate"
                :confirm-allowed="confirmAllowed"
                :workflow="workflow"
                :confirm-blocked-title="confirmBlockedTitle"
                @action="emit('rowAction', $event)"
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
