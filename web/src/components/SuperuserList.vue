<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchUsers, setUserRole, setUserSuperuser } from '../api/users'

const { t } = useI18n()
const queryClient = useQueryClient()

const { data: users, isLoading } = useQuery({
  queryKey: ['users'],
  queryFn: fetchUsers,
})

const mutation = useMutation({
  mutationFn: async (payload: {
    userId: number
    isSuperuser?: boolean
    role?: 'materialwart' | 'verantwortliche'
  }) => {
    if (payload.isSuperuser !== undefined) {
      await setUserSuperuser(payload.userId, payload.isSuperuser)
    }
    if (payload.role !== undefined) {
      await setUserRole(payload.userId, payload.role)
    }
  },
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
          class="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between"
        >
          <span class="truncate font-medium">{{ label(user) }}</span>
          <div class="flex flex-wrap items-center gap-3">
            <select
              class="select select-bordered select-sm"
              :value="user.role"
              :disabled="mutation.isPending.value"
              @change="
                mutation.mutate({
                  userId: user.id,
                  role: ($event.target as HTMLSelectElement).value as
                    | 'materialwart'
                    | 'verantwortliche',
                })
              "
            >
              <option value="materialwart">{{ t('roles.materialwart') }}</option>
              <option value="verantwortliche">{{ t('roles.verantwortliche') }}</option>
            </select>
            <label class="label cursor-pointer gap-2">
              <span class="label-text text-sm">{{ t('superusers.role') }}</span>
              <input
                type="checkbox"
                class="toggle toggle-primary toggle-sm"
                :checked="user.isSuperuser"
                :disabled="mutation.isPending.value"
                @change="
                  mutation.mutate({
                    userId: user.id,
                    isSuperuser: ($event.target as HTMLInputElement).checked,
                  })
                "
              />
            </label>
          </div>
        </li>
      </ul>
      <p v-if="mutation.isError.value" class="text-sm text-error">
        {{ t('superusers.updateFailed') }}
      </p>
    </div>
  </div>
</template>
