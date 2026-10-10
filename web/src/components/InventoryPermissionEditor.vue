<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchUsers } from '../api/users'
import type { User } from '../schemas/user'

const userIds = defineModel<number[]>({ required: true })

const { t } = useI18n()
const { data: users, isLoading } = useQuery({ queryKey: ['users'], queryFn: fetchUsers })

function label(user: Pick<User, 'name' | 'email'>) {
  return user.name ?? user.email ?? '—'
}

const sortedUsers = computed(() =>
  [...(users.value ?? [])].sort((a, b) => label(a).localeCompare(label(b), 'de')),
)

function toggle(userId: number, on: boolean) {
  const next = new Set(userIds.value)
  if (on) next.add(userId)
  else next.delete(userId)
  userIds.value = [...next]
}
</script>

<template>
  <fieldset class="rounded-lg border border-base-200 px-3 pb-3 pt-2">
    <legend class="px-1 text-sm font-medium">{{ t('inventories.permissionsHeading') }}</legend>
    <p v-if="isLoading" class="mt-1 text-sm">{{ t('auth.loading') }}</p>
    <ul v-else class="mt-1 divide-y divide-base-200">
      <li
        v-for="user in sortedUsers"
        :key="user.id"
        class="flex items-center justify-between gap-4 py-2"
      >
        <span class="truncate text-sm">{{ label(user) }}</span>
        <input
          type="checkbox"
          class="toggle toggle-primary toggle-sm"
          :checked="userIds.includes(user.id)"
          :aria-label="label(user)"
          @change="toggle(user.id, ($event.target as HTMLInputElement).checked)"
        />
      </li>
    </ul>
  </fieldset>
</template>
