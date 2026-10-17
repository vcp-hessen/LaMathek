<script setup lang="ts">
import { useMutation, useQuery } from '@tanstack/vue-query'
import type { ColumnDef } from '@tanstack/vue-table'
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useInventoryCanManage } from '../composables/useInventoryCanManage'
import { useI18n } from 'vue-i18n'
import { createLoan, fetchBorrowers, fetchLoans } from '../api/loans'
import { fetchMe } from '../api/me'
import { useCreateMinimalLoan } from '../composables/useCreateMinimalLoan'
import { loanCanHoldLines, useActiveBox } from '../composables/useActiveBox'
import { useApiErrorMessage } from '../composables/useApiErrorMessage'
import { useInventoryQueryKey } from '../composables/useInventoryQueryKey'
import DataTableFooter from '../components/data-table/DataTableFooter.vue'
import DataTableSearch from '../components/data-table/DataTableSearch.vue'
import { localeSortRow } from '../components/data-table/localeSort'
import SortHeaderButton from '../components/data-table/SortHeaderButton.vue'
import { useClientTable } from '../components/data-table/useClientTable'
import PhotoThumbnail from '../components/PhotoThumbnail.vue'
import type { Loan } from '../schemas/loan'
import { loanDisplayName } from '../utils/loanDisplayName'

const props = defineProps<{ inventoryId: number }>()

const { t } = useI18n()
const router = useRouter()
const { canManage, inventories } = useInventoryCanManage(() => props.inventoryId)

const inventory = computed(() => inventories.value?.find((row) => row.id === props.inventoryId))

const canAccess = computed(() => inventory.value != null)

const canCreate = computed(() => {
  const inv = inventory.value
  if (!inv) return false
  return inv.visibility !== 'archived'
})

watch(
  canAccess,
  (allowed) => {
    if (allowed === false && Number.isFinite(props.inventoryId)) {
      void router.replace(`/inventories/${props.inventoryId}/material`)
    }
  },
  { immediate: true },
)

const { messageFor } = useApiErrorMessage()
const formError = ref<string | null>(null)

const loansQueryKey = useInventoryQueryKey('loans', () => props.inventoryId)

const { data: loans, isLoading } = useQuery({
  queryKey: loansQueryKey,
  queryFn: () => fetchLoans(props.inventoryId),
  enabled: () => Number.isFinite(props.inventoryId) && canAccess.value,
})

const { setActiveLoan } = useActiveBox(() => props.inventoryId)
const createMutation = useCreateMinimalLoan(props.inventoryId)
const otherBorrowerId = ref('')

const { data: me } = useQuery({ queryKey: ['me'], queryFn: fetchMe })

const { data: borrowers } = useQuery({
  queryKey: ['borrowers'],
  queryFn: fetchBorrowers,
  enabled: () => canManage.value,
})

const createForOtherMutation = useMutation({
  mutationFn: () =>
    createLoan(props.inventoryId, {
      groupName: '—',
      borrowerUserId: Number(otherBorrowerId.value),
      kind: 'short',
    }),
  onSuccess: async (loan) => {
    formError.value = null
    otherBorrowerId.value = ''
    await router.push(`/inventories/${props.inventoryId}/loans/${loan.id}`)
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
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

const columns = computed<ColumnDef<Loan>[]>(() => {
  const cols: ColumnDef<Loan>[] = [
    { id: 'id', accessorFn: (loan) => loan.id },
    {
      id: 'displayTitle',
      accessorFn: (loan) => loanDisplayName(loan) || loan.groupName,
      sortingFn: localeSortRow,
    },
    { id: 'groupName', accessorFn: (loan) => loan.groupName, sortingFn: localeSortRow },
    {
      id: 'borrowerUserName',
      accessorFn: (loan) => loan.borrowerUserName,
      sortingFn: localeSortRow,
    },
    { id: 'phase', accessorFn: (loan) => phaseLabel(loan.phase), sortingFn: localeSortRow },
    { id: 'kind', accessorFn: (loan) => kindLabel(loan.kind), sortingFn: localeSortRow },
    { id: 'eventName', accessorFn: (loan) => loan.eventName ?? '', sortingFn: localeSortRow },
    { id: 'pickupOn', accessorFn: (loan) => loan.pickupOn ?? '', sortingFn: localeSortRow },
    { id: 'returnOn', accessorFn: (loan) => loan.returnOn ?? '', sortingFn: localeSortRow },
  ]
  return cols
})

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
      loan.borrowerUserName,
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

async function onNewLoan() {
  formError.value = null
  const otherId = otherBorrowerId.value.trim()
  if (canManage.value && otherId && Number(otherId) !== me.value?.id) {
    createForOtherMutation.mutate()
    return
  }
  try {
    const loan = await createMutation.mutateAsync()
    await router.push(`/inventories/${props.inventoryId}/loans/${loan.id}`)
  } catch (error) {
    formError.value = messageFor(error)
  }
}

function sortedState(columnId: string): false | 'asc' | 'desc' {
  return table.getColumn(columnId)?.getIsSorted() ?? false
}

function openLoan(loanId: number) {
  void router.push(`/inventories/${props.inventoryId}/loans/${loanId}`)
}

function useAsBox(loan: Loan, event: Event) {
  event.stopPropagation()
  if (!loanCanHoldLines(loan.phase)) return
  setActiveLoan(loan.id)
}

function onRowKeydown(event: KeyboardEvent, loanId: number) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    openLoan(loanId)
  }
}

function formatDate(value: string | null) {
  return value?.trim() ? value : '—'
}
</script>

<template>
  <div class="app-page space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-bold">{{ t('loans.heading') }}</h1>
      <div class="flex flex-wrap items-end gap-2">
        <label v-if="canManage" class="flex min-w-48 flex-col gap-1">
          <span class="text-xs opacity-80">{{ t('loans.borrower') }}</span>
          <select v-model="otherBorrowerId" class="select select-bordered select-sm">
            <option value="">{{ t('loans.borrowerSelf') }}</option>
            <option v-for="person in borrowers ?? []" :key="person.id" :value="String(person.id)">
              {{ person.name || person.email }}
            </option>
          </select>
        </label>
        <button
          v-if="canCreate"
          type="button"
          class="btn btn-primary"
          :disabled="createMutation.isPending.value || createForOtherMutation.isPending.value"
          @click="onNewLoan"
        >
          {{ t('loans.newDraft') }}
        </button>
      </div>
    </div>
    <p v-if="formError" class="text-sm text-error">{{ formError }}</p>
    <p class="text-sm opacity-70">
      {{ canManage ? t('loans.materialHint') : t('loans.myLoansInInventoryHint') }}
    </p>

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
            :placeholder="
              canManage ? t('loans.searchPlaceholder') : t('loans.searchPlaceholderBorrower')
            "
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
                <th class="hidden lg:table-cell">
                  <SortHeaderButton
                    :label="t('loans.columnGroup')"
                    :sorted="sortedState('groupName')"
                    @toggle="table.getColumn('groupName')?.toggleSorting()"
                  />
                </th>
                <th v-if="canManage" class="hidden md:table-cell">
                  <SortHeaderButton
                    :label="t('loans.columnBorrower')"
                    :sorted="sortedState('borrowerUserName')"
                    @toggle="table.getColumn('borrowerUserName')?.toggleSorting()"
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
                <th class="w-0">
                  <span class="sr-only">{{ t('loans.useAsBox') }}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="tableRows.length === 0">
                <td :colspan="canManage ? 9 : 8" class="py-8 text-center text-sm opacity-70">
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
                @click="openLoan(row.original.id)"
                @keydown="onRowKeydown($event, row.original.id)"
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
                    {{ phaseLabel(row.original.phase) }}
                    · {{ kindLabel(row.original.kind) }}
                    <template v-if="canManage">
                      · {{ row.original.borrowerUserName }}
                    </template>
                  </span>
                </td>
                <td v-if="canManage" class="hidden md:table-cell">
                  {{ row.original.borrowerUserName }}
                </td>
                <td class="hidden sm:table-cell">{{ phaseLabel(row.original.phase) }}</td>
                <td class="hidden lg:table-cell">
                  {{
                    row.original.groupName.trim() && row.original.groupName !== '—'
                      ? row.original.groupName
                      : '—'
                  }}
                </td>
                <td class="hidden lg:table-cell">{{ kindLabel(row.original.kind) }}</td>
                <td class="hidden sm:table-cell tabular-nums">
                  {{ formatDate(row.original.pickupOn) }}
                </td>
                <td class="hidden md:table-cell tabular-nums">
                  {{ formatDate(row.original.returnOn) }}
                </td>
                <td class="text-right">
                  <button
                    v-if="loanCanHoldLines(row.original.phase)"
                    type="button"
                    class="btn btn-ghost btn-xs whitespace-nowrap"
                    @click="useAsBox(row.original, $event)"
                  >
                    {{ t('loans.useAsBox') }}
                  </button>
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
