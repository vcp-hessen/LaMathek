<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchUsers, setUserSuperuser } from '../api/users'

const { t } = useI18n()
const queryClient = useQueryClient()

const { data: users, isLoading } = useQuery({
  queryKey: ['users'],
  queryFn: fetchUsers,
})

const mutation = useMutation({
  mutationFn: ({ userId, isSuperuser }: { userId: number; isSuperuser: boolean }) =>
    setUserSuperuser(userId, isSuperuser),
  onSuccess: async () => {
    await queryClient.invalidateQueries({ queryKey: ['users'] })
    await queryClient.invalidateQueries({ queryKey: ['me'] })
  },
})

const sortedUsers = computed(() =>
  [...(users.value ?? [])].sort((a, b) => a.id - b.id),
)

function label(user: { name?: string | null; email?: string | null; sub?: string }) {
  return user.name ?? user.email ?? user.sub ?? '—'
}

async function onToggle(userId: number, next: boolean) {
  await mutation.mutateAsync({ userId, isSuperuser: next })
}
</script>

<template>
  <div class="card bg-base-100 shadow-md">
    <div class="card-body gap-3 text-left">
      <h2 class="card-title text-lg">{{ t('superusers.heading') }}</h2>
      <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>
      <ul v-else class="divide-y divide-base-200">
        <li
          v-for="user in sortedUsers"
          :key="user.id"
          class="flex items-center justify-between gap-4 py-2"
        >
          <span class="truncate">{{ label(user) }}</span>
          <label class="label cursor-pointer gap-2">
            <span class="label-text text-sm">{{ t('superusers.role') }}</span>
            <input
              type="checkbox"
              class="toggle toggle-primary"
              :checked="user.isSuperuser"
              :disabled="mutation.isPending.value"
              @change="
                onToggle(user.id, ($event.target as HTMLInputElement).checked)
              "
            />
          </label>
        </li>
      </ul>
      <p v-if="mutation.isError.value" class="text-sm text-error">
        {{ t('superusers.updateFailed') }}
      </p>
    </div>
  </div>
</template>
