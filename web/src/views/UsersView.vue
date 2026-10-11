<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchInventories } from '../api/inventories'
import { apiErrorCode } from '../api/errors'
import { fetchMe } from '../api/me'
import { fetchUsers, grantUserInventory, revokeUserInventory, setUserSuperuser } from '../api/users'
import ExpandableRow from '../components/ExpandableRow.vue'
import type { ManagedUser } from '../schemas/user'

const PAGE_SIZE = 20

const { t } = useI18n()
const queryClient = useQueryClient()
const actionError = ref<string | null>(null)
const pendingKey = ref<string | null>(null)
const search = ref('')
const page = ref(1)
const expandedId = ref<number | null>(null)

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
  return user.name ?? user.email ?? '—'
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

const filteredUsers = computed(() => {
  const query = search.value.trim().toLowerCase()
  const list = users.value ?? []
  if (!query) return list
  return list.filter((user) => {
    const name = (user.name ?? '').toLowerCase()
    const email = (user.email ?? '').toLowerCase()
    return name.includes(query) || email.includes(query)
  })
})

const pageCount = computed(() =>
  Math.max(1, Math.ceil(filteredUsers.value.length / PAGE_SIZE)),
)

const currentPage = computed(() => Math.min(page.value, pageCount.value))

const pageUsers = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE
  return filteredUsers.value.slice(start, start + PAGE_SIZE)
})

const pageFrom = computed(() =>
  filteredUsers.value.length === 0 ? 0 : (currentPage.value - 1) * PAGE_SIZE + 1,
)
const pageTo = computed(() =>
  Math.min(currentPage.value * PAGE_SIZE, filteredUsers.value.length),
)

watch(search, () => {
  page.value = 1
  expandedId.value = null
})

function toggleRow(userId: number) {
  expandedId.value = expandedId.value === userId ? null : userId
}

function goToPage(next: number) {
  page.value = Math.min(Math.max(1, next), pageCount.value)
  expandedId.value = null
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
    <div v-else class="card bg-base-100 shadow-md">
      <div class="card-body gap-3 p-4 text-left">
        <label class="flex min-w-0 flex-col gap-1 sm:max-w-sm">
          <span class="sr-only">{{ t('users.searchLabel') }}</span>
          <input
            v-model="search"
            type="search"
            class="input input-bordered input-sm w-full"
            :placeholder="t('users.searchPlaceholder')"
            autocomplete="off"
          />
        </label>
        <p v-if="filteredUsers.length === 0" class="text-sm opacity-70">
          {{ t('users.noMatches') }}
        </p>
        <ul v-else class="list-none">
          <ExpandableRow
            v-for="user in pageUsers"
            :key="user.id"
            :expanded="expandedId === user.id"
            @toggle="toggleRow(user.id)"
          >
            <template #summary>
              <div class="flex min-w-0 items-baseline gap-3">
                <span class="truncate font-medium">{{ label(user) }}</span>
                <span
                  v-if="user.name && user.email"
                  class="hidden min-w-0 truncate text-sm opacity-70 sm:inline"
                >
                  {{ user.email }}
                </span>
                <span v-if="user.isSuperuser" class="badge badge-ghost badge-sm shrink-0">
                  {{ t('users.superuserLabel') }}
                </span>
                <span class="ml-auto shrink-0 text-sm opacity-70">
                  {{ t('users.inventoryCount', { count: user.inventoryIds.length }) }}
                </span>
              </div>
            </template>
            <template #editor>
              <div class="flex flex-col gap-3">
                <label class="label cursor-pointer justify-start gap-2 py-0">
                  <span class="label-text text-sm">{{ t('users.superuserLabel') }}</span>
                  <input
                    type="checkbox"
                    class="toggle toggle-primary toggle-sm"
                    :checked="user.isSuperuser"
                    :disabled="pendingKey !== null"
                    @change="onSuperuserChange(user, $event)"
                  />
                </label>
                <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div class="min-w-0 flex-1">
                    <p class="text-xs opacity-80">{{ t('users.inventoriesLabel') }}</p>
                    <ul v-if="inventoriesOf(user).length" class="mt-1 flex flex-wrap gap-1">
                      <li v-for="inventory in inventoriesOf(user)" :key="inventory.id">
                        <span class="badge badge-outline gap-1">
                          {{ inventory.name }}
                          <button
                            type="button"
                            class="btn btn-ghost btn-xs px-1"
                            :aria-label="t('users.removeInventory', { name: inventory.name })"
                            :disabled="pendingKey !== null"
                            @click="onRemoveInventory(user, inventory.id)"
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
                      :disabled="pendingKey !== null || addableInventories(user).length === 0"
                      @change="onAddInventory(user, $event)"
                    >
                      <option value="">{{ t('users.addInventoryPlaceholder') }}</option>
                      <option
                        v-for="inventory in addableInventories(user)"
                        :key="inventory.id"
                        :value="inventory.id"
                      >
                        {{ inventory.name }}
                      </option>
                    </select>
                  </label>
                </div>
              </div>
            </template>
          </ExpandableRow>
        </ul>
        <div
          v-if="filteredUsers.length > 0"
          class="flex items-center justify-between gap-2"
        >
          <p class="text-xs opacity-70">
            {{ t('users.pageRange', { from: pageFrom, to: pageTo, total: filteredUsers.length }) }}
          </p>
          <div class="join">
            <button
              type="button"
              class="btn btn-sm join-item"
              :disabled="currentPage <= 1"
              :aria-label="t('users.previousPage')"
              @click="goToPage(currentPage - 1)"
            >
              ‹
            </button>
            <button
              type="button"
              class="btn btn-sm join-item"
              :disabled="currentPage >= pageCount"
              :aria-label="t('users.nextPage')"
              @click="goToPage(currentPage + 1)"
            >
              ›
            </button>
          </div>
        </div>
        <p v-if="actionError" class="text-sm text-error">{{ actionError }}</p>
      </div>
    </div>
  </div>
</template>
