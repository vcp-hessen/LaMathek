import { useQuery } from '@tanstack/vue-query'
import { computed, type MaybeRefOrGetter, toValue } from 'vue'
import { fetchInventories } from '../api/inventories'

export function useInventoryCanManage(
  inventoryId: MaybeRefOrGetter<number | null | undefined>,
) {
  const { data: inventories } = useQuery({
    queryKey: ['inventories'],
    queryFn: fetchInventories,
  })

  const canManage = computed(() => {
    const id = toValue(inventoryId)
    if (id == null || !Number.isFinite(id)) return false
    const inv = inventories.value?.find((row) => row.id === id)
    return inv?.canManage === true
  })

  return { canManage, inventories }
}
