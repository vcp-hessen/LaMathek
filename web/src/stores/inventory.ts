import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const STORAGE_ACTIVE = 'lamathek.activeInventoryId'

function readStoredId(): number | null {
  const raw = localStorage.getItem(STORAGE_ACTIVE)
  if (!raw) return null
  const id = Number(raw)
  return Number.isFinite(id) ? id : null
}

export const useInventoryStore = defineStore('inventory', () => {
  const activeInventoryId = ref<number | null>(readStoredId())

  watch(activeInventoryId, (id) => {
    if (id === null) localStorage.removeItem(STORAGE_ACTIVE)
    else localStorage.setItem(STORAGE_ACTIVE, String(id))
  })

  function setActiveInventory(id: number | null) {
    activeInventoryId.value = id
  }

  function reconcileWithAccessible(inventories: { id: number }[]) {
    const allowed = new Set(inventories.map((i) => i.id))
    if (activeInventoryId.value !== null && !allowed.has(activeInventoryId.value)) {
      activeInventoryId.value = inventories[0]?.id ?? null
      return
    }
    if (activeInventoryId.value === null && inventories.length === 1) {
      activeInventoryId.value = inventories[0].id
    }
  }

  return {
    activeInventoryId,
    setActiveInventory,
    reconcileWithAccessible,
  }
})
