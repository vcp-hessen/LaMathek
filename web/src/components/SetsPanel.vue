<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { ColumnDef } from '@tanstack/vue-table'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { createSet, fetchSets } from '../api/sets'
import { useApiErrorMessage } from '../composables/useApiErrorMessage'
import { useInventoryQueryKey } from '../composables/useInventoryQueryKey'
import DataTableFooter from './data-table/DataTableFooter.vue'
import DataTableSearch from './data-table/DataTableSearch.vue'
import { localeSortRow } from './data-table/localeSort'
import SortHeaderButton from './data-table/SortHeaderButton.vue'
import { useClientTable } from './data-table/useClientTable'
import PhotoThumbnail from './PhotoThumbnail.vue'
import type { SetSummary } from '../schemas/set'

const props = defineProps<{ inventoryId: number }>()

const { t } = useI18n()
const router = useRouter()
const queryClient = useQueryClient()
const { messageFor } = useApiErrorMessage()
const formError = ref<string | null>(null)
const newName = ref('')
const newShortName = ref('')

const setsQueryKey = useInventoryQueryKey('sets', () => props.inventoryId)

const { data: sets, isLoading } = useQuery({
  queryKey: setsQueryKey,
  queryFn: () => fetchSets(props.inventoryId),
})

const columns = computed<ColumnDef<SetSummary>[]>(() => [
  {
    id: 'name',
    accessorFn: (set) => set.name,
    sortingFn: localeSortRow,
  },
  {
    id: 'shortName',
    accessorFn: (set) => set.shortName ?? '',
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
} = useClientTable<SetSummary>({
  data: () => sets.value ?? [],
  columns,
  getRowId: (set) => String(set.id),
  globalFilterFn: () => (row, _columnId, filterValue) => {
    const query = String(filterValue ?? '').trim().toLowerCase()
    if (!query) return true
    const set = row.original
    const haystack = [set.name, set.shortName ?? ''].join(' ').toLowerCase()
    return haystack.includes(query)
  },
  initialSorting: [{ id: 'name', desc: false }],
})

const createMutation = useMutation({
  mutationFn: () =>
    createSet(props.inventoryId, {
      name: newName.value,
      shortName: newShortName.value.trim() || null,
    }),
  onSuccess: async () => {
    formError.value = null
    newName.value = ''
    newShortName.value = ''
    await queryClient.invalidateQueries({ queryKey: ['sets', props.inventoryId] })
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
})

function sortedState(columnId: string): false | 'asc' | 'desc' {
  return table.getColumn(columnId)?.getIsSorted() ?? false
}

function openSet(setId: number) {
  void router.push(`/inventories/${props.inventoryId}/sets/${setId}`)
}

function onRowKeydown(event: KeyboardEvent, setId: number) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    openSet(setId)
  }
}
</script>

<template>
  <div class="flex flex-col gap-4 text-left">
    <h2 class="app-section-header app-page-title">{{ t('sets.heading') }}</h2>
    <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>
    <template v-else>
      <p v-if="!(sets?.length)" class="text-sm opacity-70">{{ t('sets.empty') }}</p>
      <div v-else class="rounded-lg border border-base-200">
        <div
          class="data-table-toolbar flex flex-col gap-3 border-b border-base-200 p-3 sm:flex-row sm:flex-wrap sm:items-end"
        >
          <DataTableSearch
            :model-value="globalFilter"
            :label="t('sets.searchLabel')"
            :placeholder="t('sets.searchPlaceholder')"
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
                    :label="t('sets.columnName')"
                    :sorted="sortedState('name')"
                    @toggle="table.getColumn('name')?.toggleSorting()"
                  />
                </th>
                <th class="hidden sm:table-cell">
                  <SortHeaderButton
                    :label="t('sets.columnShortName')"
                    :sorted="sortedState('shortName')"
                    @toggle="table.getColumn('shortName')?.toggleSorting()"
                  />
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="tableRows.length === 0">
                <td colspan="3" class="py-8 text-center text-sm opacity-70">
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
                @click="openSet(row.original.id)"
                @keydown="onRowKeydown($event, row.original.id)"
              >
                <td class="data-table-col-photo hidden sm:table-cell">
                  <PhotoThumbnail :photo-id="row.original.coverPhotoId" />
                </td>
                <td class="data-table-col-lead min-w-0">
                  <span class="font-medium">{{ row.original.name }}</span>
                  <span v-if="row.original.shortName" class="mt-0.5 block text-xs opacity-70 sm:hidden">
                    {{ row.original.shortName }}
                  </span>
                </td>
                <td class="hidden sm:table-cell">{{ row.original.shortName || '—' }}</td>
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
      <form
        class="flex flex-col gap-2 border-t border-base-200 pt-4 sm:flex-row sm:flex-wrap"
        @submit.prevent="createMutation.mutate()"
      >
        <p v-if="formError" class="w-full text-sm text-error">{{ formError }}</p>
        <input
          v-model="newShortName"
          type="text"
          class="input input-bordered w-full sm:w-28"
          :placeholder="t('sets.shortNameOptional')"
        />
        <input
          v-model="newName"
          type="text"
          class="input input-bordered min-w-0 flex-1"
          :placeholder="t('sets.newName')"
          required
        />
        <button type="submit" class="btn btn-primary" :disabled="createMutation.isPending.value">
          {{ t('sets.create') }}
        </button>
      </form>
    </template>
  </div>
</template>
