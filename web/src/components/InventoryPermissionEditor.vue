<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  fetchInventoryPermissions,
  replaceInventoryPermissions,
} from '../api/inventories'
import { fetchUsers } from '../api/users'

const props = defineProps<{ inventoryId: number }>()

const { t } = useI18n()
const queryClient = useQueryClient()
const selected = ref<Set<number>>(new Set())

const { data: users } = useQuery({ queryKey: ['users'], queryFn: fetchUsers })
const { data: permittedIds } = useQuery({
  queryKey: ['inventoryPermissions', props.inventoryId],
  queryFn: () => fetchInventoryPermissions(props.inventoryId),
})

watch(
  permittedIds,
  (ids) => {
    if (ids) selected.value = new Set(ids)
  },
  { immediate: true },
)

const sortedUsers = computed(() =>
  [...(users.value ?? [])].sort((a, b) => a.id - b.id),
)

const saveMutation = useMutation({
  mutationFn: () =>
    replaceInventoryPermissions(props.inventoryId, [...selected.value]),
  onSuccess: async () => {
    await queryClient.invalidateQueries({
      queryKey: ['inventoryPermissions', props.inventoryId],
    })
    await queryClient.invalidateQueries({ queryKey: ['inventories'] })
  },
})

function toggle(userId: number, on: boolean) {
  const next = new Set(selected.value)
  if (on) next.add(userId)
  else next.delete(userId)
  selected.value = next
}

function label(user: { name?: string | null; email?: string | null }) {
  return user.name ?? user.email ?? '—'
}
</script>

<template>
  <div class="card bg-base-100 shadow-md">
    <div class="card-body gap-3 text-left">
      <h2 class="card-title text-lg">{{ t('inventories.permissionsHeading') }}</h2>
      <ul class="divide-y divide-base-200">
        <li
          v-for="user in sortedUsers"
          :key="user.id"
          class="flex items-center justify-between gap-4 py-2"
        >
          <span class="truncate">{{ label(user) }}</span>
          <input
            type="checkbox"
            class="toggle toggle-primary"
            :checked="selected.has(user.id)"
            @change="toggle(user.id, ($event.target as HTMLInputElement).checked)"
          />
        </li>
      </ul>
      <div class="card-actions justify-end">
        <button
          type="button"
          class="btn btn-primary"
          :disabled="saveMutation.isPending.value"
          @click="saveMutation.mutate()"
        >
          {{ t('inventories.savePermissions') }}
        </button>
      </div>
    </div>
  </div>
</template>
