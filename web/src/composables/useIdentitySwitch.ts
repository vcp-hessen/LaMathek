import { useQueryClient } from '@tanstack/vue-query'

import { useActiveLoanStore } from '../stores/activeLoan'
import { useInventoryStore } from '../stores/inventory'

/**
 * After starting or ending an impersonation every cached answer belonged to the
 * other identity: drop the whole query cache and the per-Inventar box choice.
 */
export function useIdentitySwitch() {
  const queryClient = useQueryClient()
  const activeLoanStore = useActiveLoanStore()
  const inventoryStore = useInventoryStore()

  return function identityChanged() {
    activeLoanStore.clearAll()
    inventoryStore.setActiveInventory(null)
    queryClient.clear()
  }
}
