<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { searchUsers } from '../api/users'
import { fetchInventoryAccess } from '../api/inventories'
import type { User } from '../schemas/user'

const props = withDefaults(
  defineProps<{
    inventoryId: number | null
    headingKey?: string
  }>(),
  { headingKey: 'inventories.permissionsHeading' },
)

const userIds = defineModel<number[]>({ required: true })

const { t } = useI18n()
const searchQuery = ref('')
const knownUsers = ref(new Map<number, User>())

const { data: loadedUsers } = useQuery({
  queryKey: computed(() => ['inventoryPermissionUsers', props.inventoryId]),
  queryFn: () => fetchInventoryAccess(props.inventoryId!),
  enabled: () => props.inventoryId !== null,
})

watch(
  loadedUsers,
  (users) => {
    if (!users) return
    for (const user of [...users.users, ...users.readers]) {
      knownUsers.value.set(user.id, user)
    }
  },
  { immediate: true },
)

const trimmedQuery = computed(() => searchQuery.value.trim())
const { data: searchHits, isFetching: searchLoading } = useQuery({
  queryKey: computed(() => ['usersSearch', trimmedQuery.value]),
  queryFn: () => searchUsers(trimmedQuery.value),
  enabled: () => trimmedQuery.value.length >= 2,
})

function label(user: Pick<User, 'name' | 'email'>) {
  return user.name ?? user.email ?? '—'
}

const displayUsers = computed(() =>
  userIds.value.map((id) => {
    const user = knownUsers.value.get(id)
    return user ?? { id, name: null, email: null, isSuperuser: false }
  }),
)

const addableHits = computed(() =>
  (searchHits.value ?? []).filter((user) => !userIds.value.includes(user.id)),
)

function removeUser(id: number) {
  userIds.value = userIds.value.filter((row) => row !== id)
}

function addUser(user: User) {
  if (userIds.value.includes(user.id)) return
  knownUsers.value.set(user.id, user)
  userIds.value = [...userIds.value, user.id]
  searchQuery.value = ''
}
</script>

<template>
  <fieldset class="rounded-lg border border-base-200 px-3 pb-3 pt-2">
    <legend class="px-1 text-sm font-medium">{{ t(headingKey) }}</legend>

    <ul v-if="displayUsers.length" class="mt-2 divide-y divide-base-200">
      <li
        v-for="user in displayUsers"
        :key="user.id"
        class="flex items-center justify-between gap-4 py-2"
      >
        <span class="truncate text-sm">{{ label(user) }}</span>
        <button
          type="button"
          class="btn btn-ghost btn-xs"
          :aria-label="t('inventories.permissionRemove', { name: label(user) })"
          @click="removeUser(user.id)"
        >
          {{ t('inventories.permissionRemoveShort') }}
        </button>
      </li>
    </ul>
    <p v-else class="mt-2 text-sm opacity-70">{{ t('inventories.permissionsEmpty') }}</p>

    <div class="mt-3 space-y-2">
      <label class="flex min-w-0 flex-col gap-1">
        <span class="text-xs opacity-80">{{ t('inventories.permissionSearchLabel') }}</span>
        <input
          v-model="searchQuery"
          type="search"
          class="input input-bordered input-sm w-full"
          :placeholder="t('inventories.permissionSearchPlaceholder')"
          autocomplete="off"
        />
      </label>
      <p v-if="searchLoading" class="text-xs opacity-70">{{ t('auth.loading') }}</p>
      <ul
        v-else-if="trimmedQuery.length >= 2 && addableHits.length"
        class="rounded-lg border border-base-200"
      >
        <li
          v-for="user in addableHits"
          :key="user.id"
          class="flex items-center justify-between gap-2 border-b border-base-200 px-3 py-2 last:border-b-0"
        >
          <span class="truncate text-sm">{{ label(user) }}</span>
          <button type="button" class="btn btn-primary btn-xs" @click="addUser(user)">
            {{ t('inventories.permissionAdd') }}
          </button>
        </li>
      </ul>
      <p
        v-else-if="trimmedQuery.length >= 2 && !searchLoading"
        class="text-xs opacity-70"
      >
        {{ t('inventories.permissionSearchNoHits') }}
      </p>
    </div>
  </fieldset>
</template>
