import { defineStore } from 'pinia'
import { ref } from 'vue'

const STORAGE_PREFIX = 'lamathek.activeLoan.'

function storageKey(inventoryId: number): string {
  return `${STORAGE_PREFIX}${inventoryId}`
}

// sessionStorage can be unavailable (private mode, blocked site data): the box
// choice then just lasts for this page.
function readStoredLoanId(inventoryId: number): number | null {
  let raw: string | null = null
  try {
    raw = sessionStorage.getItem(storageKey(inventoryId))
  } catch {
    return null
  }
  if (!raw) return null
  const id = Number(raw)
  return Number.isFinite(id) ? id : null
}

export const useActiveLoanStore = defineStore('activeLoan', () => {
  const activeByInventory = ref<Record<number, number | null>>({})

  function getActiveLoanId(inventoryId: number): number | null {
    if (inventoryId in activeByInventory.value) {
      return activeByInventory.value[inventoryId] ?? null
    }
    return readStoredLoanId(inventoryId)
  }

  function setActiveLoanId(inventoryId: number, loanId: number | null) {
    activeByInventory.value = { ...activeByInventory.value, [inventoryId]: loanId }
    try {
      if (loanId === null) sessionStorage.removeItem(storageKey(inventoryId))
      else sessionStorage.setItem(storageKey(inventoryId), String(loanId))
    } catch {
      // see readStoredLoanId
    }
  }

  function clearActiveLoan(inventoryId: number) {
    setActiveLoanId(inventoryId, null)
  }

  /** Forget every box, e.g. when the signed-in identity changes (impersonation). */
  function clearAll() {
    activeByInventory.value = {}
    try {
      for (const key of Object.keys(sessionStorage)) {
        if (key.startsWith(STORAGE_PREFIX)) sessionStorage.removeItem(key)
      }
    } catch {
      // see readStoredLoanId
    }
  }

  return {
    clearAll,
    getActiveLoanId,
    setActiveLoanId,
    clearActiveLoan,
  }
})
