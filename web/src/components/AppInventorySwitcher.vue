<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import type { Inventory } from '../schemas/inventory'
import { useInventoryStore } from '../stores/inventory'

const props = withDefaults(
  defineProps<{
    inventories: Inventory[]
    loading?: boolean
    sidebar?: boolean
  }>(),
  { sidebar: false },
)

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const inventoryStore = useInventoryStore()

const inventorySectionRoutes = new Set([
  'inventory-material-types',
  'inventory-pieces',
  'inventory-stock',
  'inventory-sets',
  'inventory-loans',
])

const inventoryDetailRoutes = new Set(['set-detail', 'loan-detail', 'piece-detail'])

const hasInventories = computed(() => props.inventories.length > 0)

const selectValue = computed(() => {
  if (!hasInventories.value) return ''
  const id = inventoryStore.activeInventoryId
  if (id !== null && props.inventories.some((i) => i.id === id)) return String(id)
  return ''
})

function onChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  if (!value) return
  const id = Number(value)
  inventoryStore.setActiveInventory(id)
  const name = route.name ? String(route.name) : ''
  if (inventorySectionRoutes.has(name)) {
    void router.push({ name, params: { ...route.params, id: String(id) } })
    return
  }
  if (inventoryDetailRoutes.has(name)) {
    void router.push(`/inventories/${id}/material-types`)
    return
  }
  void router.push(`/inventories/${id}/material-types`)
}
</script>

<template>
  <div :class="sidebar ? 'w-full px-1' : 'flex shrink-0 items-center gap-2'">
    <template v-if="loading">
      <span :class="sidebar ? 'text-sm text-white/60' : 'text-sm text-base-content/60'">
        {{ t('auth.loading') }}
      </span>
    </template>
    <template v-else-if="!hasInventories">
      <span
        class="badge badge-sm w-full max-w-none truncate font-normal"
        :class="
          sidebar
            ? 'justify-center border-white/30 bg-transparent text-white/70'
            : 'badge-outline max-w-[14rem] text-base-content/70'
        "
        role="status"
      >
        {{ t('inventories.noneAccessible') }}
      </span>
    </template>
    <template v-else>
      <label class="sr-only" for="active-inventory">{{ t('inventories.activeLabel') }}</label>
      <select
        id="active-inventory"
        class="select select-sm w-full"
        :class="
          sidebar
            ? 'inventory-switcher border-white/30 text-white'
            : 'select-bordered max-w-[10rem] sm:max-w-[14rem]'
        "
        :value="selectValue"
        :aria-label="t('inventories.activeLabel')"
        @change="onChange"
      >
        <option v-if="selectValue === ''" disabled value="">
          {{ t('inventories.pickActive') }}
        </option>
        <option v-for="inv in inventories" :key="inv.id" :value="inv.id">
          {{ inv.name }}
        </option>
      </select>
    </template>
  </div>
</template>
