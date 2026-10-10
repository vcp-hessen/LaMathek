<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchStocks, setStockQuantity } from '../api/material'
import { useApiErrorMessage } from '../composables/useApiErrorMessage'
import { useInventoryQueryKey } from '../composables/useInventoryQueryKey'
import ExpandableRow from './ExpandableRow.vue'

const props = defineProps<{ inventoryId: number }>()

const { t } = useI18n()
const { messageFor } = useApiErrorMessage()
const queryClient = useQueryClient()

const expandedMaterialTypeId = ref<number | null>(null)
const editError = ref<string | null>(null)
const editQuantities = ref<Record<number, number>>({})

const stocksQueryKey = useInventoryQueryKey('stocks', () => props.inventoryId)

const { data: stocks, isLoading } = useQuery({
  queryKey: stocksQueryKey,
  queryFn: () => fetchStocks(props.inventoryId),
})

watch(
  stocks,
  (rows) => {
    if (!rows) return
    const editNext: Record<number, number> = { ...editQuantities.value }
    for (const row of rows) {
      if (expandedMaterialTypeId.value !== row.materialTypeId) {
        editNext[row.materialTypeId] = row.quantity
      }
    }
    editQuantities.value = editNext
  },
  { immediate: true },
)

function toggleRow(materialTypeId: number) {
  if (expandedMaterialTypeId.value === materialTypeId) {
    expandedMaterialTypeId.value = null
    editError.value = null
    return
  }
  expandedMaterialTypeId.value = materialTypeId
  editError.value = null
  const row = stocks.value?.find((r) => r.materialTypeId === materialTypeId)
  if (row) {
    editQuantities.value[materialTypeId] = row.quantity
  }
}

const saveMutation = useMutation({
  mutationFn: ({ materialTypeId, quantity }: { materialTypeId: number; quantity: number }) =>
    setStockQuantity(props.inventoryId, materialTypeId, quantity),
  onSuccess: async () => {
    editError.value = null
    await queryClient.invalidateQueries({ queryKey: ['stocks', props.inventoryId] })
  },
  onError: (error) => {
    editError.value = messageFor(error)
  },
})

function saveRow(materialTypeId: number) {
  const quantity = editQuantities.value[materialTypeId]
  if (typeof quantity !== 'number' || quantity < 0 || !Number.isInteger(quantity)) return
  saveMutation.mutate({ materialTypeId, quantity })
}
</script>

<template>
  <div class="card bg-base-100 shadow-md">
    <div class="card-body gap-4 text-left">
      <h2 class="card-title text-lg">{{ t('material.stockHeading') }}</h2>
      <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>
      <ul v-else class="list-none">
        <ExpandableRow
          v-for="row in stocks"
          :key="row.materialTypeId"
          :expanded="expandedMaterialTypeId === row.materialTypeId"
          @toggle="toggleRow(row.materialTypeId)"
        >
          <template #summary>
            <div class="flex flex-wrap items-baseline justify-between gap-2">
              <span class="font-medium">{{ row.materialTypeName }}</span>
              <span class="text-sm text-base-content/70">
                {{ t('material.stockQuantity') }}: {{ row.quantity
                }}<template v-if="row.unit"> {{ row.unit }}</template>
              </span>
            </div>
          </template>
          <template #editor>
            <form class="space-y-3" @submit.prevent="saveRow(row.materialTypeId)">
              <label class="form-control w-full max-w-xs">
                <span class="label-text">{{ t('material.stockQuantity') }}</span>
                <input
                  v-model.number="editQuantities[row.materialTypeId]"
                  type="number"
                  min="0"
                  step="1"
                  class="input input-bordered"
                  required
                />
              </label>
              <p v-if="editError && expandedMaterialTypeId === row.materialTypeId" class="text-sm text-error">
                {{ editError }}
              </p>
              <div class="flex justify-end">
                <button
                  type="submit"
                  class="btn btn-primary btn-sm"
                  :disabled="saveMutation.isPending.value"
                >
                  {{ t('material.save') }}
                </button>
              </div>
            </form>
          </template>
        </ExpandableRow>
        <li v-if="!stocks?.length" class="py-2 text-sm opacity-70">
          {{ t('material.stockEmpty') }}
        </li>
      </ul>
    </div>
  </div>
</template>
