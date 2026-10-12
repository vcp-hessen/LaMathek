<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { ColumnDef } from '@tanstack/vue-table'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchInventories } from '../api/inventories'
import { apiErrorCode } from '../api/errors'
import { fetchMe } from '../api/me'
import { startImpersonation } from '../api/impersonation'
import { fetchUsers, grantUserInventory, revokeUserInventory, setUserSuperuser } from '../api/users'
import { userLabel } from '../utils/userLabel'
import DataTableFooter from '../components/data-table/DataTableFooter.vue'
import DataTableSearch from '../components/data-table/DataTableSearch.vue'
import { localeSortRow } from '../components/data-table/localeSort'
import SortHeaderButton from '../components/data-table/SortHeaderButton.vue'
import { useClientTable } from '../components/data-table/useClientTable'
import type { ManagedUser } from '../schemas/user'

const { t } = useI18n()
const queryClient = useQueryClient()
const actionError = ref<string | null>(null)
const pendingKey = ref<string | null>(null)
const expandedId = ref<number | null>(null)
const impersonateReason = ref('')

const { data: me, isLoading: meLoading } = useQuery({
  queryKey: ['me'],
  queryFn: fetchMe,
})

const { data: users, isLoading: usersLoading } = useQuery({
  queryKey: ['users'],
  queryFn: fetchUsers,
  enabled: () => !!me.value?.isSuperuser,
})

const { data: inventories } = useQuery({
  queryKey: ['inventories'],
  queryFn: fetchInventories,
  enabled: () => !!me.value?.isSuperuser,
})

const inventoryName = computed(() => {
  const names = new Map<number, string>()
  for (const inventory of inventories.value ?? []) {
    names.set(inventory.id, inventory.name)
  }
  return names
})

function label(user: { name?: string | null; email?: string | null }) {
  return userLabel(user)
}

function canImpersonate(user: ManagedUser) {
  if (!me.value?.isSuperuser || me.value.impersonation) return false
  if (user.id === me.value.id) return false
  return !user.isSuperuser
}

function inventoriesOf(user: ManagedUser) {
  return user.inventoryIds.map((id) => ({
    id,
    name: inventoryName.value.get(id) ?? `#${id}`,
  }))
}

function addableInventories(user: ManagedUser) {
  const assigned = new Set(user.inventoryIds)
  return (inventories.value ?? []).filter((inventory) => !assigned.has(inventory.id))
}

const columns = computed<ColumnDef<ManagedUser>[]>(() => [
  {
    id: 'name',
    accessorFn: (user) => label(user),
    sortingFn: localeSortRow,
  },
  {
    id: 'email',
    accessorFn: (user) => user.email ?? '',
    sortingFn: localeSortRow,
  },
  {
    id: 'superuser',
    accessorFn: (user) => (user.isSuperuser ? t('users.superuserLabel') : ''),
    sortingFn: localeSortRow,
  },
  {
    id: 'inventories',
    accessorFn: (user) => user.inventoryIds.length,
  },
])

const {
  table,
  globalFilter,
  sorting,
  pagination,
  tableRows,
  filteredCount,
  pageCount,
  currentPage,
  pageFrom,
  pageTo,
  goToPage,
  setPageSize,
} = useClientTable<ManagedUser>({
  data: () => users.value ?? [],
  columns,
  getRowId: (user) => String(user.id),
  globalFilterFn: () => (row, _columnId, filterValue) => {
    const query = String(filterValue ?? '').trim().toLowerCase()
    if (!query) return true
    const user = row.original
    const name = (user.name ?? '').toLowerCase()
    const email = (user.email ?? '').toLowerCase()
    return name.includes(query) || email.includes(query)
  },
  initialSorting: [{ id: 'name', desc: false }],
})

watch(
  [globalFilter, sorting, () => pagination.value.pageIndex, () => pagination.value.pageSize],
  () => {
    expandedId.value = null
  },
)

watch(expandedId, () => {
  impersonateReason.value = ''
})

function toggleRow(userId: number) {
  expandedId.value = expandedId.value === userId ? null : userId
}

function sortedState(columnId: string): false | 'asc' | 'desc' {
  return table.getColumn(columnId)?.getIsSorted() ?? false
}

function onRowKeydown(event: KeyboardEvent, userId: number) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    toggleRow(userId)
  }
}

async function refreshAccess() {
  await queryClient.invalidateQueries({ queryKey: ['users'] })
  await queryClient.invalidateQueries({ queryKey: ['inventoryPermissionUsers'] })
  await queryClient.invalidateQueries({ queryKey: ['me'] })
}

function fail(error: unknown) {
  const code = apiErrorCode(error)
  if (code === 'cannot_remove_last_superuser') {
    actionError.value = t('users.cannotRemoveLastSuperuser')
    return
  }
  if (code === 'cannot_clear_permissions') {
    actionError.value = t('users.cannotClearPermissions')
    return
  }
  if (code === 'invalid_reason') {
    actionError.value = t('users.impersonateReasonRequired')
    return
  }
  if (code === 'cannot_impersonate_superuser') {
    actionError.value = t('users.impersonateSuperuserForbidden')
    return
  }
  if (code === 'cannot_impersonate_self') {
    actionError.value = t('users.impersonateSelfForbidden')
    return
  }
  if (code === 'impersonation_active') {
    actionError.value = t('users.impersonationAlreadyActive')
    return
  }
  actionError.value = t('users.updateFailed')
}

const superuserMutation = useMutation({
  mutationFn: async (payload: { userId: number; isSuperuser: boolean }) => {
    pendingKey.value = `superuser:${payload.userId}`
    await setUserSuperuser(payload.userId, payload.isSuperuser)
  },
  onSuccess: refreshAccess,
  onError: fail,
  onSettled: () => {
    pendingKey.value = null
  },
})

const grantMutation = useMutation({
  mutationFn: async (payload: { userId: number; inventoryId: number }) => {
    pendingKey.value = `grant:${payload.userId}`
    await grantUserInventory(payload.userId, payload.inventoryId)
  },
  onSuccess: refreshAccess,
  onError: fail,
  onSettled: () => {
    pendingKey.value = null
  },
})

const impersonateMutation = useMutation({
  mutationFn: async (payload: { userId: number; reason: string }) => {
    pendingKey.value = `impersonate:${payload.userId}`
    await startImpersonation(payload.userId, payload.reason)
  },
  onSuccess: async () => {
    expandedId.value = null
    impersonateReason.value = ''
    await queryClient.invalidateQueries({ queryKey: ['me'] })
    await queryClient.invalidateQueries({ queryKey: ['inventories'] })
    await queryClient.invalidateQueries({ queryKey: ['audit-events'] })
  },
  onError: fail,
  onSettled: () => {
    pendingKey.value = null
  },
})

const revokeMutation = useMutation({
  mutationFn: async (payload: { userId: number; inventoryId: number }) => {
    pendingKey.value = `revoke:${payload.userId}:${payload.inventoryId}`
    await revokeUserInventory(payload.userId, payload.inventoryId)
  },
  onSuccess: refreshAccess,
  onError: fail,
  onSettled: () => {
    pendingKey.value = null
  },
})

function onSuperuserChange(user: ManagedUser, event: Event) {
  actionError.value = null
  const checked = (event.target as HTMLInputElement).checked
  superuserMutation.mutate({ userId: user.id, isSuperuser: checked })
}

function onAddInventory(user: ManagedUser, event: Event) {
  const select = event.target as HTMLSelectElement
  const inventoryId = Number(select.value)
  select.value = ''
  if (!Number.isFinite(inventoryId) || inventoryId <= 0) return
  actionError.value = null
  grantMutation.mutate({ userId: user.id, inventoryId })
}

function onRemoveInventory(user: ManagedUser, inventoryId: number) {
  actionError.value = null
  revokeMutation.mutate({ userId: user.id, inventoryId })
}

function onStartImpersonation(user: ManagedUser) {
  actionError.value = null
  const reason = impersonateReason.value.trim()
  if (!reason) {
    actionError.value = t('users.impersonateReasonRequired')
    return
  }
  impersonateMutation.mutate({ userId: user.id, reason })
}
</script>

<template>
  <div class="app-page space-y-4">
    <h1 class="text-2xl font-bold">{{ t('users.heading') }}</h1>
    <p v-if="meLoading || (me?.isSuperuser && usersLoading)" class="text-sm">
      {{ t('auth.loading') }}
    </p>
    <p v-else-if="!me?.isSuperuser" class="text-sm text-base-content/70">
      {{ t('users.superuserOnly') }}
    </p>
    <div v-else class="flex flex-col gap-3 text-left">
      <p v-if="!(users?.length)" class="text-sm opacity-70">{{ t('users.noMatches') }}</p>
      <div v-else class="rounded-lg border border-base-200">
        <div
          class="data-table-toolbar flex flex-col gap-3 border-b border-base-200 p-3 sm:flex-row sm:flex-wrap sm:items-end"
        >
          <DataTableSearch
            :model-value="globalFilter"
            :label="t('users.searchLabel')"
            :placeholder="t('users.searchPlaceholder')"
            @update:model-value="globalFilter = $event"
          />
        </div>
        <div class="overflow-x-auto">
          <table class="table table-sm data-table">
            <thead>
              <tr>
                <th class="data-table-col-lead">
                  <SortHeaderButton
                    :label="t('users.columnName')"
                    :sorted="sortedState('name')"
                    @toggle="table.getColumn('name')?.toggleSorting()"
                  />
                </th>
                <th class="hidden sm:table-cell">
                  <SortHeaderButton
                    :label="t('users.columnEmail')"
                    :sorted="sortedState('email')"
                    @toggle="table.getColumn('email')?.toggleSorting()"
                  />
                </th>
                <th class="hidden md:table-cell">
                  <SortHeaderButton
                    :label="t('users.superuserLabel')"
                    :sorted="sortedState('superuser')"
                    @toggle="table.getColumn('superuser')?.toggleSorting()"
                  />
                </th>
                <th>
                  <SortHeaderButton
                    :label="t('users.columnInventories')"
                    :sorted="sortedState('inventories')"
                    @toggle="table.getColumn('inventories')?.toggleSorting()"
                  />
                </th>
              </tr>
            </thead>
            <tbody v-if="tableRows.length === 0">
              <tr>
                <td colspan="4" class="py-8 text-center text-sm opacity-70">
                  {{ t('dataTable.noResults') }}
                </td>
              </tr>
            </tbody>
            <tbody v-for="(row, index) in tableRows" v-else :key="row.id">
              <tr
                tabindex="0"
                role="button"
                class="data-table-row cursor-pointer"
                :class="{ 'data-table-row--stripe': index % 2 === 1 }"
                :aria-expanded="expandedId === row.original.id"
                @click="toggleRow(row.original.id)"
                @keydown="onRowKeydown($event, row.original.id)"
              >
                <td class="data-table-col-lead min-w-0">
                  <div class="flex items-start gap-2">
                    <span
                      class="mt-0.5 shrink-0 text-base-content/50 transition-transform duration-200"
                      :class="{ 'rotate-90': expandedId === row.original.id }"
                      aria-hidden="true"
                    >
                      ›
                    </span>
                    <div class="min-w-0">
                      <span class="font-medium">{{ label(row.original) }}</span>
                      <div class="mt-0.5 space-y-0.5 text-xs opacity-70">
                        <span v-if="row.original.email" class="block sm:hidden">
                          {{ row.original.email }}
                        </span>
                        <span v-if="row.original.isSuperuser" class="block md:hidden">
                          {{ t('users.superuserLabel') }}
                        </span>
                      </div>
                    </div>
                  </div>
                </td>
                <td class="hidden sm:table-cell">{{ row.original.email || '—' }}</td>
                <td class="hidden md:table-cell">
                  <span v-if="row.original.isSuperuser" class="badge badge-ghost badge-sm">
                    {{ t('users.superuserLabel') }}
                  </span>
                  <span v-else>—</span>
                </td>
                <td>{{ t('users.inventoryCount', { count: row.original.inventoryIds.length }) }}</td>
              </tr>
              <tr v-if="expandedId === row.original.id" class="data-table-editor">
                <td colspan="4" class="pb-4 pt-3">
                  <div class="flex flex-col gap-3 pl-5">
                    <label class="label cursor-pointer justify-start gap-2 py-0">
                      <span class="label-text text-sm">{{ t('users.superuserLabel') }}</span>
                      <input
                        type="checkbox"
                        class="toggle toggle-primary toggle-sm"
                        :checked="row.original.isSuperuser"
                        :disabled="pendingKey !== null"
                        @change="onSuperuserChange(row.original, $event)"
                      />
                    </label>
                    <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div class="min-w-0 flex-1">
                        <p class="text-xs opacity-80">{{ t('users.inventoriesLabel') }}</p>
                        <ul v-if="inventoriesOf(row.original).length" class="mt-1 flex flex-wrap gap-1">
                          <li v-for="inventory in inventoriesOf(row.original)" :key="inventory.id">
                            <span class="badge badge-outline gap-1">
                              {{ inventory.name }}
                              <button
                                type="button"
                                class="btn btn-ghost btn-xs px-1"
                                :aria-label="t('users.removeInventory', { name: inventory.name })"
                                :disabled="pendingKey !== null"
                                @click="onRemoveInventory(row.original, inventory.id)"
                              >
                                ×
                              </button>
                            </span>
                          </li>
                        </ul>
                        <p v-else class="mt-1 text-sm opacity-70">{{ t('users.inventoriesEmpty') }}</p>
                      </div>
                      <label class="flex min-w-0 flex-col gap-1 sm:w-56">
                        <span class="sr-only">{{ t('users.addInventoryPlaceholder') }}</span>
                        <select
                          class="select select-bordered select-sm w-full"
                          :disabled="pendingKey !== null || addableInventories(row.original).length === 0"
                          @change="onAddInventory(row.original, $event)"
                        >
                          <option value="">{{ t('users.addInventoryPlaceholder') }}</option>
                          <option
                            v-for="inventory in addableInventories(row.original)"
                            :key="inventory.id"
                            :value="inventory.id"
                          >
                            {{ inventory.name }}
                          </option>
                        </select>
                      </label>
                    </div>
                    <div
                      v-if="canImpersonate(row.original)"
                      class="flex items-center gap-2 border-t border-base-200 pt-3"
                    >
                      <label class="sr-only">{{ t('users.impersonateReasonLabel') }}</label>
                      <input
                        v-model="impersonateReason"
                        type="text"
                        class="input input-bordered input-sm min-w-0 flex-1"
                        :placeholder="t('users.impersonateReasonPlaceholder')"
                        :disabled="pendingKey !== null"
                        @keydown.enter.stop.prevent="onStartImpersonation(row.original)"
                      />
                      <button
                        type="button"
                        class="btn btn-outline btn-sm shrink-0 sm:w-auto"
                        :disabled="pendingKey !== null"
                        @click.stop="onStartImpersonation(row.original)"
                      >
                        {{ t('users.impersonateAction') }}
                      </button>
                    </div>
                  </div>
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
      <p v-if="actionError" class="text-sm text-error">{{ actionError }}</p>
    </div>
  </div>
</template>
