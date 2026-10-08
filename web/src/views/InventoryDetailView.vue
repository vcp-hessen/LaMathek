<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { fetchInventory, renameInventory } from '../api/inventories'
import { fetchMe } from '../api/me'
import AppNavbar from '../components/AppNavbar.vue'
import InventoryPermissionEditor from '../components/InventoryPermissionEditor.vue'

const route = useRoute()
const { t } = useI18n()
const queryClient = useQueryClient()

const inventoryId = computed(() => Number(route.params.id))

const { data: me } = useQuery({ queryKey: ['me'], queryFn: fetchMe })
const { data: inventory, isLoading } = useQuery({
  queryKey: ['inventory', inventoryId],
  queryFn: () => fetchInventory(inventoryId.value),
  enabled: () => Number.isFinite(inventoryId.value),
})

const name = ref('')
watch(
  inventory,
  (inv) => {
    if (inv) name.value = inv.name
  },
  { immediate: true },
)

const renameMutation = useMutation({
  mutationFn: () => renameInventory(inventoryId.value, name.value),
  onSuccess: async () => {
    await queryClient.invalidateQueries({ queryKey: ['inventories'] })
    await queryClient.invalidateQueries({ queryKey: ['inventory', inventoryId] })
  },
})
</script>

<template>
  <div class="min-h-screen bg-base-200">
    <AppNavbar />
    <main class="mx-auto max-w-lg space-y-6 p-6">
      <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>
      <template v-else-if="inventory">
        <h1 class="text-2xl font-bold">{{ t('inventories.detail') }}</h1>
        <form class="flex gap-2" @submit.prevent="renameMutation.mutate()">
          <input v-model="name" type="text" class="input input-bordered flex-1" required />
          <button type="submit" class="btn btn-primary" :disabled="renameMutation.isPending.value">
            {{ t('inventories.rename') }}
          </button>
        </form>
        <InventoryPermissionEditor
          v-if="me?.isSuperuser"
          :inventory-id="inventory.id"
        />
      </template>
    </main>
  </div>
</template>
