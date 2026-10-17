import { defineStore } from 'pinia'
import { ref } from 'vue'

const STORAGE_PREFIX = 'lamathek.activeLoan.'

function storageKey(inventoryId: number): string {
  return `${STORAGE_PREFIX}${inventoryId}`
}

function readStoredLoanId(inventoryId: number): number | null {
  const raw = sessionStorage.getItem(storageKey(inventoryId))
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
    if (loanId === null) sessionStorage.removeItem(storageKey(inventoryId))
    else sessionStorage.setItem(storageKey(inventoryId), String(loanId))
  }

  function clearActiveLoan(inventoryId: number) {
    setActiveLoanId(inventoryId, null)
  }

  return {
    getActiveLoanId,
    setActiveLoanId,
    clearActiveLoan,
  }
})
