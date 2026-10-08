<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { createInventory, fetchInventories } from '../api/inventories'
import { fetchMe } from '../api/me'
import AppNavbar from '../components/AppNavbar.vue'

const { t } = useI18n()
const queryClient = useQueryClient()
const newName = ref('')

const { data: me } = useQuery({ queryKey: ['me'], queryFn: fetchMe })
const { data: inventories, isLoading } = useQuery({
  queryKey: ['inventories'],
  queryFn: fetchInventories,
  enabled: () => !!me.value,
})

const createMutation = useMutation({
  mutationFn: () => createInventory(newName.value),
  onSuccess: async () => {
    newName.value = ''
    await queryClient.invalidateQueries({ queryKey: ['inventories'] })
  },
})
</script>

<template>
  <div class="min-h-screen bg-base-200">
    <AppNavbar />
    <main class="mx-auto max-w-2xl p-6">
      <h1 class="mb-4 text-2xl font-bold">{{ t('inventories.title') }}</h1>
      <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>
      <ul v-else class="menu rounded-box bg-base-100 shadow">
        <li v-for="inv in inventories" :key="inv.id">
          <RouterLink :to="`/inventories/${inv.id}`">{{ inv.name }}</RouterLink>
        </li>
        <li v-if="!inventories?.length" class="px-4 py-3 text-sm opacity-70">
          {{ t('inventories.empty') }}
        </li>
      </ul>

      <form
        v-if="me?.isSuperuser"
        class="mt-6 flex gap-2"
        @submit.prevent="createMutation.mutate()"
      >
        <input
          v-model="newName"
          type="text"
          class="input input-bordered flex-1"
          :placeholder="t('inventories.newName')"
          required
        />
        <button type="submit" class="btn btn-primary" :disabled="createMutation.isPending.value">
          {{ t('inventories.create') }}
        </button>
      </form>
    </main>
  </div>
</template>
