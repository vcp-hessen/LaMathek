<script setup lang="ts">
import QueryError from '../components/QueryError.vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { deleteStockLot, fetchStocks, updateStockLot } from '../api/material'
import MaterialDetailsSection from '../components/material/MaterialDetailsSection.vue'
import MaterialItemMetadataFields from '../components/material/MaterialItemMetadataFields.vue'
import StockQuantityInput from '../components/material/StockQuantityInput.vue'
import StockLossesSection from '../components/material/StockLossesSection.vue'
import {
  emptyItemMetadataDraft,
  itemMetadataFromRecord,
  itemMetadataToWritePayload,
  type ItemMetadataDraft,
} from '../utils/materialItemValue'
import { stockLotListItemFromStocks } from '../components/material/materialTableSetup'
import AddToBoxButton from '../components/loans/AddToBoxButton.vue'
import PhotoGallery from '../components/PhotoGallery.vue'
import SuperuserDestructiveDelete from '../components/SuperuserDestructiveDelete.vue'
import VariantAxisSelects from '../components/VariantAxisSelects.vue'
import { useApiErrorMessage } from '../composables/useApiErrorMessage'
import { useInventoryCanManage } from '../composables/useInventoryCanManage'
import { useInventoryQueryKey } from '../composables/useInventoryQueryKey'
import { syncVariantMapKeys } from '../utils/variantDisplay'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const { messageFor } = useApiErrorMessage()
const queryClient = useQueryClient()

const inventoryId = computed(() => Number(route.params.id))
const lotId = computed(() => Number(route.params.lotId))
const { canManage } = useInventoryCanManage(inventoryId)

const stocksQueryKey = useInventoryQueryKey('stocks', inventoryId)

const { data: stocks, isLoading, isError, error: loadError, refetch: retryLoad } = useQuery({
  queryKey: stocksQueryKey,
  queryFn: () => fetchStocks(inventoryId.value),
  enabled: () => Number.isFinite(inventoryId.value),
})

const lot = computed(() => {
  if (!Number.isFinite(lotId.value) || !stocks.value) return null
  return stockLotListItemFromStocks(stocks.value, lotId.value)
})

const draft = reactive({ label: '', variant: {} as Record<string, string>, quantity: 0 })
const editMeta = ref<ItemMetadataDraft>(emptyItemMetadataDraft())
const savedEdit = ref<string | null>(null)
const formError = ref<string | null>(null)

function lotVariantPayload(map: Record<string, string>): Record<string, string> {
  const payload: Record<string, string> = {}
  for (const [label, value] of Object.entries(map)) {
    const trimmed = value?.trim()
    if (trimmed) payload[label] = trimmed
  }
  return payload
}

function editSnapshot() {
  const variant = lotVariantPayload(draft.variant)
  const variantEntries = Object.keys(variant)
    .sort()
    .map((label) => [label, variant[label]])
  return JSON.stringify({
    label: draft.label.trim(),
    variant: variantEntries,
    quantity: draft.quantity,
    meta: editMeta.value,
  })
}

const dirty = computed(() => savedEdit.value !== null && editSnapshot() !== savedEdit.value)

function loadDraftFromLot() {
  const item = lot.value
  if (!item) return
  draft.label = item.label ?? ''
  draft.variant = syncVariantMapKeys(item.variant, item.variants)
  draft.quantity = item.quantity
  editMeta.value = itemMetadataFromRecord(item)
  savedEdit.value = editSnapshot()
  formError.value = null
}

watch(lot, () => loadDraftFromLot(), { immediate: true })

async function refreshStocks() {
  await queryClient.invalidateQueries({ queryKey: [...stocksQueryKey.value] })
}

const updateMutation = useMutation({
  mutationFn: () =>
    updateStockLot(inventoryId.value, lotId.value, {
      label: draft.label.trim() || null,
      variant: lotVariantPayload(draft.variant),
      quantity: draft.quantity,
      ...itemMetadataToWritePayload(editMeta.value, { includeStatus: true }),
    }),
  onSuccess: async () => {
    formError.value = null
    savedEdit.value = editSnapshot()
    await refreshStocks()
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
})

const deleteMutation = useMutation({
  mutationFn: () => deleteStockLot(inventoryId.value, lotId.value),
  onSuccess: async () => {
    await refreshStocks()
    await router.push(`/inventories/${inventoryId.value}/material`)
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
})
</script>

<template>
  <div class="app-page space-y-6">
    <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>
    <QueryError v-else-if="isError" :error="loadError" @retry="retryLoad()" />
    <template v-else-if="lot">
      <div class="flex justify-end">
        <AddToBoxButton
          :inventory-id="inventoryId"
          :material-type-id="lot.materialTypeId"
          :stock-variant="lot.variant"
          :available-quantity="lot.quantity - (lot.lostQuantity ?? 0)"
          size="md"
        />
      </div>
      <MaterialDetailsSection
        :form-error="formError"
        :saving="updateMutation.isPending.value"
        :dirty="dirty"
        :readonly="!canManage"
        @save="updateMutation.mutate()"
      >
        <fieldset :disabled="!canManage" class="space-y-3 border-0 p-0">
        <label class="flex min-w-0 flex-col gap-1">
          <span class="text-xs opacity-80">{{ t('material.stockLotLabel') }}</span>
          <input
            v-model="draft.label"
            type="text"
            class="input input-bordered input-sm w-full"
            :placeholder="t('material.stockLotLabelPlaceholder')"
          />
        </label>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <label class="flex min-w-0 flex-col gap-1">
            <span class="text-xs opacity-80">{{ t('material.pieceType') }}</span>
            <select class="select select-bordered select-sm w-full" disabled>
              <option>{{ lot.materialTypeName }}</option>
            </select>
          </label>
          <label class="flex min-w-0 flex-col gap-1">
            <span class="text-xs opacity-80">{{ t('material.stockQuantity') }}</span>
            <StockQuantityInput v-model="draft.quantity" :unit="lot.unit" compact />
            <span v-if="lot.lostQuantity" class="text-xs text-warning">
              {{ t('material.lostOfLot', { count: lot.lostQuantity }) }}
            </span>
          </label>
          <VariantAxisSelects
            v-if="lot.variants.length"
            v-model="draft.variant"
            :axes="lot.variants"
            compact
            inline
          />
        </div>
        <MaterialItemMetadataFields
          v-model:acquired-year="editMeta.acquiredYear"
          v-model:note="editMeta.note"
          v-model:source="editMeta.source"
          v-model:serial-number="editMeta.serialNumber"
          v-model:new-value-euro="editMeta.newValueEuro"
          v-model:status="editMeta.status"
          show-status
        />
        </fieldset>
        <template #delete>
          <SuperuserDestructiveDelete
            v-if="canManage"
            :label="t('material.stockLotRemove')"
            :warning="t('destructive.stockLotWarning')"
            :disabled="deleteMutation.isPending.value"
            @confirmed="deleteMutation.mutate()"
          />
        </template>
      </MaterialDetailsSection>

      <StockLossesSection
        :inventory-id="inventoryId"
        :material-type-id="lot.materialTypeId"
        :lot-id="lot.id"
        :can-manage="canManage"
        @changed="refreshStocks"
      />
      <section class="app-section gap-4 border-b border-base-200 pb-6 last:border-b-0">
        <h2 class="app-page-title text-base">{{ t('photos.heading') }}</h2>
        <PhotoGallery
          :owner="{
            kind: 'stockLot',
            inventoryId,
            lotId: lot.id,
          }"
          :photos="lot.photos ?? []"
          :readonly="!canManage"
          @change="refreshStocks"
        />
      </section>
    </template>
    <p v-else class="text-sm opacity-70">{{ t('material.piecesNoSearchResults') }}</p>
  </div>
</template>
