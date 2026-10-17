<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import type { ColumnDef } from '@tanstack/vue-table'
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { fetchMyLoans } from '../api/loans'
import DataTableFooter from '../components/data-table/DataTableFooter.vue'
import DataTableSearch from '../components/data-table/DataTableSearch.vue'
import { localeSortRow } from '../components/data-table/localeSort'
import SortHeaderButton from '../components/data-table/SortHeaderButton.vue'
import { useClientTable } from '../components/data-table/useClientTable'
import PhotoThumbnail from '../components/PhotoThumbnail.vue'
import type { Loan } from '../schemas/loan'
import { loanDisplayName } from '../utils/loanDisplayName'

const { t } = useI18n()
const router = useRouter()

const { data: loans, isLoading } = useQuery({
  queryKey: ['my-loans'],
  queryFn: fetchMyLoans,
})

function phaseLabel(phase: string) {
  if (phase === 'active') return t('loans.phaseActive')
  if (phase === 'closed') return t('loans.phaseClosed')
  return t('loans.phaseDraft')
}

function kindLabel(kind: string) {
  return kind === 'permanent' ? t('loans.kindPermanent') : t('loans.kindShort')
}

function loanGroupSubtitle(loan: Loan): string | null {
  const group = loan.groupName.trim()
  if (!group || group === '—') return null
  if (loan.eventName?.trim()) return group
  return null
}

const columns = computed<ColumnDef<Loan>[]>(() => [
  { id: 'id', accessorFn: (loan) => loan.id },
  {
    id: 'displayTitle',
    accessorFn: (loan) => loanDisplayName(loan) || loan.groupName,
    sortingFn: localeSortRow,
  },
  {
    id: 'inventoryName',
    accessorFn: (loan) => loan.inventoryName ?? '',
    sortingFn: localeSortRow,
  },
  { id: 'groupName', accessorFn: (loan) => loan.groupName, sortingFn: localeSortRow },
  { id: 'phase', accessorFn: (loan) => phaseLabel(loan.phase), sortingFn: localeSortRow },
  { id: 'kind', accessorFn: (loan) => kindLabel(loan.kind), sortingFn: localeSortRow },
  { id: 'pickupOn', accessorFn: (loan) => loan.pickupOn ?? '', sortingFn: localeSortRow },
  { id: 'returnOn', accessorFn: (loan) => loan.returnOn ?? '', sortingFn: localeSortRow },
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
} = useClientTable<Loan>({
  data: () => loans.value ?? [],
  columns,
  getRowId: (loan) => String(loan.id),
  globalFilterFn: () => (row, _columnId, filterValue) => {
    const query = String(filterValue ?? '').trim().toLowerCase()
    if (!query) return true
    const loan = row.original
    const haystack = [
      loan.groupName,
      loan.inventoryName ?? '',
      loan.eventName ?? '',
      phaseLabel(loan.phase),
      kindLabel(loan.kind),
      loan.pickupOn ?? '',
      loan.returnOn ?? '',
    ]
      .join(' ')
      .toLowerCase()
    return haystack.includes(query)
  },
  initialSorting: [{ id: 'id', desc: true }],
})

function sortedState(columnId: string): false | 'asc' | 'desc' {
  return table.getColumn(columnId)?.getIsSorted() ?? false
}

function openLoan(loan: Loan) {
  void router.push(`/inventories/${loan.inventoryId}/loans/${loan.id}`)
}

function onRowKeydown(event: KeyboardEvent, loan: Loan) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    openLoan(loan)
  }
}

function formatDate(value: string | null) {
  return value?.trim() ? value : '—'
}
</script>

<template>
  <div class="app-page space-y-6">
    <h1 class="text-2xl font-bold">{{ t('loans.myLoansHeading') }}</h1>
    <p class="text-sm opacity-70">{{ t('loans.myLoansHint') }}</p>

    <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>
    <template v-else>
      <p v-if="!(loans?.length)" class="text-sm opacity-70">{{ t('loans.empty') }}</p>
      <div v-else class="rounded-lg border border-base-200">
        <div
          class="data-table-toolbar flex flex-col gap-3 border-b border-base-200 p-3 sm:flex-row sm:flex-wrap sm:items-end"
        >
          <DataTableSearch
            :model-value="globalFilter"
            :label="t('loans.searchLabel')"
            :placeholder="t('loans.searchPlaceholderBorrower')"
            @update:model-value="globalFilter = $event"
          />
        </div>
        <div class="overflow-x-auto">
          <table class="table table-sm data-table">
            <thead>
              <tr>
                <th class="data-table-col-photo hidden sm:table-cell">
                  <span class="sr-only">{{ t('dataTable.photo') }}</span>
                </th>
                <th class="data-table-col-lead">
                  <SortHeaderButton
                    :label="t('loans.columnTitle')"
                    :sorted="sortedState('displayTitle')"
                    @toggle="table.getColumn('displayTitle')?.toggleSorting()"
                  />
                </th>
                <th class="hidden md:table-cell">
                  <SortHeaderButton
                    :label="t('loans.columnInventory')"
                    :sorted="sortedState('inventoryName')"
                    @toggle="table.getColumn('inventoryName')?.toggleSorting()"
                  />
                </th>
                <th class="hidden lg:table-cell">
                  <SortHeaderButton
                    :label="t('loans.columnGroup')"
                    :sorted="sortedState('groupName')"
                    @toggle="table.getColumn('groupName')?.toggleSorting()"
                  />
                </th>
                <th class="hidden sm:table-cell">
                  <SortHeaderButton
                    :label="t('loans.columnPhase')"
                    :sorted="sortedState('phase')"
                    @toggle="table.getColumn('phase')?.toggleSorting()"
                  />
                </th>
                <th class="hidden lg:table-cell">
                  <SortHeaderButton
                    :label="t('loans.columnKind')"
                    :sorted="sortedState('kind')"
                    @toggle="table.getColumn('kind')?.toggleSorting()"
                  />
                </th>
                <th class="hidden sm:table-cell">
                  <SortHeaderButton
                    :label="t('loans.pickupOn')"
                    :sorted="sortedState('pickupOn')"
                    @toggle="table.getColumn('pickupOn')?.toggleSorting()"
                  />
                </th>
                <th class="hidden md:table-cell">
                  <SortHeaderButton
                    :label="t('loans.returnOn')"
                    :sorted="sortedState('returnOn')"
                    @toggle="table.getColumn('returnOn')?.toggleSorting()"
                  />
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
                role="link"
                class="data-table-row cursor-pointer"
                :class="{ 'data-table-row--stripe': index % 2 === 1 }"
                @click="openLoan(row.original)"
                @keydown="onRowKeydown($event, row.original)"
              >
                <td class="data-table-col-photo hidden sm:table-cell">
                  <PhotoThumbnail :photo-id="row.original.coverPhotoId" />
                </td>
                <td class="data-table-col-lead min-w-0">
                  <span class="font-medium">
                    {{ loanDisplayName(row.original) || row.original.groupName || '—' }}
                  </span>
                  <span
                    v-if="loanGroupSubtitle(row.original)"
                    class="mt-0.5 block text-xs opacity-70"
                  >
                    {{ t('loans.group') }}: {{ loanGroupSubtitle(row.original) }}
                  </span>
                  <span class="mt-0.5 block text-xs opacity-70 sm:hidden">
                    {{ row.original.inventoryName || '—' }}
                    · {{ phaseLabel(row.original.phase) }}
                  </span>
                </td>
                <td class="hidden md:table-cell">{{ row.original.inventoryName || '—' }}</td>
                <td class="hidden lg:table-cell">
                  {{
                    row.original.groupName.trim() && row.original.groupName !== '—'
                      ? row.original.groupName
                      : '—'
                  }}
                </td>
                <td class="hidden sm:table-cell">{{ phaseLabel(row.original.phase) }}</td>
                <td class="hidden lg:table-cell">{{ kindLabel(row.original.kind) }}</td>
                <td class="hidden sm:table-cell tabular-nums">
                  {{ formatDate(row.original.pickupOn) }}
                </td>
                <td class="hidden md:table-cell tabular-nums">
                  {{ formatDate(row.original.returnOn) }}
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
  </div>
</template>
