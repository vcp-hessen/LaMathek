import { computed, type MaybeRefOrGetter, toValue } from 'vue'

/** Reactive query key segment so vue-query refetches when the active Inventar changes. */
export function useInventoryQueryKey(scope: string, inventoryId: MaybeRefOrGetter<number>) {
  return computed(() => [scope, toValue(inventoryId)] as const)
}
