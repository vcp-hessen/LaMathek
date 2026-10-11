<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { createStockLot, deleteStockLot, fetchStocks, updateStockLot } from '../api/material'
import { useApiErrorMessage } from '../composables/useApiErrorMessage'
import { useInventoryQueryKey } from '../composables/useInventoryQueryKey'
import ExpandableRow from './ExpandableRow.vue'
import PhotoGallery from './PhotoGallery.vue'
import PhotoThumbnail from './PhotoThumbnail.vue'
import VariantAxisSelects from './VariantAxisSelects.vue'
import type { StockLot, VariantAxis } from '../schemas/material'
import {
  emptyVariantMap,
  syncVariantMapKeys,
  variantMapSummary,
} from '../utils/variantDisplay'

const NEW_LOT = 'new' as const
type ExpandedLotKey = number | typeof NEW_LOT | null

type StockLotListItem = StockLot & {
  materialTypeId: number
  materialTypeName: string
  unit: string | null
  variants: VariantAxis[]
}

type LotGroup = { materialTypeId: number; label: string; lots: StockLotListItem[] }

const props = defineProps<{ inventoryId: number }>()

const { t } = useI18n()
const { messageFor } = useApiErrorMessage()
const queryClient = useQueryClient()

const expandedKey = ref<ExpandedLotKey>(null)
const formError = ref<string | null>(null)
const filterMaterialTypeId = ref('')
const drafts = reactive<
  Record<number, { label: string; variant: Record<string, string>; quantity: number }>
>({})
const savedEdits = ref<Record<number, string>>({})
const newLot = reactive({
  materialTypeId: '',
  label: '',
  variant: {} as Record<string, string>,
  quantity: 1,
})

const stocksQueryKey = useInventoryQueryKey('stocks', () => props.inventoryId)

const { data: stocks, isLoading } = useQuery({
  queryKey: stocksQueryKey,
  queryFn: () => fetchStocks(props.inventoryId),
})

const stockTypes = computed(() => stocks.value ?? [])
const canAddLots = computed(() => stockTypes.value.length > 0)

const lots = computed((): StockLotListItem[] =>
  stockTypes.value.flatMap((row) =>
    row.lots.map((lot) => ({
      ...lot,
      materialTypeId: row.materialTypeId,
      materialTypeName: row.materialTypeName,
      unit: row.unit,
      variants: row.variants,
    })),
  ),
)

const filteredLots = computed(() => {
  if (!filterMaterialTypeId.value) return lots.value
  const id = Number(filterMaterialTypeId.value)
  return lots.value.filter((lot) => lot.materialTypeId === id)
})

const lotGroups = computed((): LotGroup[] => {
  const byType = new Map<number, StockLotListItem[]>()
  for (const lot of filteredLots.value) {
    const bucket = byType.get(lot.materialTypeId) ?? []
    bucket.push(lot)
    byType.set(lot.materialTypeId, bucket)
  }
  const groups: LotGroup[] = []
  for (const [materialTypeId, groupLots] of byType.entries()) {
    groupLots.sort((a, b) =>
      (a.label ?? '').localeCompare(b.label ?? '', 'de', { sensitivity: 'base' }),
    )
    groups.push({
      materialTypeId,
      label: groupLots[0]?.materialTypeName ?? '',
      lots: groupLots,
    })
  }
  groups.sort((a, b) => a.label.localeCompare(b.label, 'de'))
  return groups
})

const selectedNewType = computed(() =>
  stockTypes.value.find((row) => String(row.materialTypeId) === newLot.materialTypeId),
)

const newTypeAxes = computed(() => selectedNewType.value?.variants ?? [])

function lotVariantPayload(map: Record<string, string>): Record<string, string> {
  const payload: Record<string, string> = {}
  for (const [label, value] of Object.entries(map)) {
    const trimmed = value?.trim()
    if (trimmed) payload[label] = trimmed
  }
  return payload
}

function resetNewLotDraft() {
  const filtered = filterMaterialTypeId.value
  const matchesFilter = stockTypes.value.some((row) => String(row.materialTypeId) === filtered)
  newLot.materialTypeId = matchesFilter
    ? filtered
    : stockTypes.value[0]
      ? String(stockTypes.value[0].materialTypeId)
      : ''
  newLot.label = ''
  newLot.variant = emptyVariantMap(newTypeAxes.value)
  newLot.quantity = 1
}

function lotEditSnapshot(lotId: number) {
  const draft = drafts[lotId]
  if (!draft) return ''
  const variant = lotVariantPayload(draft.variant)
  const variantEntries = Object.keys(variant)
    .sort()
    .map((label) => [label, variant[label]])
  return JSON.stringify({
    label: draft.label.trim(),
    variant: variantEntries,
    quantity: draft.quantity,
  })
}

function lotDirty(lotId: number) {
  const saved = savedEdits.value[lotId]
  return saved !== undefined && lotEditSnapshot(lotId) !== saved
}

function fillDraft(lot: StockLotListItem) {
  drafts[lot.id] = {
    label: lot.label ?? '',
    variant: syncVariantMapKeys(lot.variant, lot.variants),
    quantity: lot.quantity,
  }
  savedEdits.value = { ...savedEdits.value, [lot.id]: lotEditSnapshot(lot.id) }
}

function lotSummaryMeta(lot: StockLotListItem): string {
  const parts: string[] = []
  const variantText = variantMapSummary(lot.variants, lot.variant)
  if (variantText) parts.push(variantText)
  const qty = `${lot.quantity}${lot.unit ? ` ${lot.unit}` : ''}`
  parts.push(qty)
  return parts.join(' · ')
}

function openNewLotRow() {
  expandedKey.value = NEW_LOT
  formError.value = null
  resetNewLotDraft()
}

function closeExpandedRow() {
  expandedKey.value = null
  formError.value = null
}

function toggleLotRow(lotId: number) {
  if (expandedKey.value === lotId) {
    closeExpandedRow()
    return
  }
  expandedKey.value = lotId
  formError.value = null
}

async function refresh() {
  formError.value = null
  await queryClient.invalidateQueries({ queryKey: ['stocks', props.inventoryId] })
}

const createMutation = useMutation({
  mutationFn: () =>
    createStockLot(props.inventoryId, Number(newLot.materialTypeId), {
      label: newLot.label.trim() || null,
      variant: lotVariantPayload(newLot.variant),
      quantity: newLot.quantity,
    }),
  onSuccess: async () => {
    expandedKey.value = null
    resetNewLotDraft()
    await refresh()
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
})

const updateMutation = useMutation({
  mutationFn: (lotId: number) => {
    const draft = drafts[lotId]
    return updateStockLot(props.inventoryId, lotId, {
      label: draft.label.trim() || null,
      variant: lotVariantPayload(draft.variant),
      quantity: draft.quantity,
    })
  },
  onSuccess: async (_data, lotId) => {
    savedEdits.value = { ...savedEdits.value, [lotId]: lotEditSnapshot(lotId) }
    await refresh()
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
})

const deleteMutation = useMutation({
  mutationFn: (lotId: number) => deleteStockLot(props.inventoryId, lotId),
  onSuccess: async (_data, lotId) => {
    if (expandedKey.value === lotId) expandedKey.value = null
    await refresh()
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
})

watch(expandedKey, (key) => {
  if (typeof key === 'number') {
    const lot = lots.value.find((row) => row.id === key)
    if (lot) fillDraft(lot)
  }
})

watch(
  () => newLot.materialTypeId,
  () => {
    newLot.variant = syncVariantMapKeys(newLot.variant, newTypeAxes.value)
  },
)
</script>

<template>
  <div class="card bg-base-100 shadow-md">
    <div class="card-body gap-4 text-left">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h2 class="card-title text-lg">{{ t('material.stockHeading') }}</h2>
        <button
          v-if="!isLoading && canAddLots"
          type="button"
          class="btn btn-ghost btn-sm"
          :aria-expanded="expandedKey === NEW_LOT"
          @click="openNewLotRow"
        >
          {{ t('material.stockLotAdd') }}
        </button>
      </div>

      <label v-if="canAddLots && !isLoading" class="flex min-w-0 flex-col gap-1 sm:max-w-xs">
        <span class="text-xs opacity-80">{{ t('material.filterMaterialType') }}</span>
        <select v-model="filterMaterialTypeId" class="select select-bordered select-sm">
          <option value="">{{ t('material.filterAllMaterialTypes') }}</option>
          <option v-for="row in stockTypes" :key="row.materialTypeId" :value="String(row.materialTypeId)">
            {{ row.materialTypeName }}
          </option>
        </select>
      </label>

      <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>
      <template v-else>
        <p v-if="!canAddLots" class="text-sm opacity-70">{{ t('material.stockNeedType') }}</p>
        <ul v-else class="list-none">
          <ExpandableRow
            v-if="expandedKey === NEW_LOT"
            :expanded="true"
            @toggle="closeExpandedRow"
          >
            <template #summary>
              <span class="font-medium">{{ t('material.stockLotAdd') }}</span>
            </template>
            <template #editor>
              <form class="space-y-3" @submit.prevent="createMutation.mutate()">
                <label class="flex min-w-0 flex-col gap-1">
                  <span class="text-xs opacity-80">{{ t('material.filterMaterialType') }}</span>
                  <select v-model="newLot.materialTypeId" class="select select-bordered w-full" required>
                    <option v-for="row in stockTypes" :key="row.materialTypeId" :value="String(row.materialTypeId)">
                      {{ row.materialTypeName }}
                    </option>
                  </select>
                </label>
                <label class="flex min-w-0 flex-col gap-1">
                  <span class="text-xs opacity-80">{{ t('material.stockLotLabel') }}</span>
                  <input
                    v-model="newLot.label"
                    type="text"
                    class="input input-bordered w-full"
                    :placeholder="t('material.stockLotLabelPlaceholder')"
                  />
                </label>
                <VariantAxisSelects
                  v-if="newTypeAxes.length"
                  v-model="newLot.variant"
                  :axes="newTypeAxes"
                  optional
                />
                <label class="flex min-w-0 flex-col gap-1">
                  <span class="text-xs opacity-80">{{ t('material.stockQuantity') }}</span>
                  <input
                    v-model.number="newLot.quantity"
                    type="number"
                    min="0"
                    step="1"
                    class="input input-bordered w-full"
                    required
                  />
                </label>
                <p v-if="formError" class="text-sm text-error">{{ formError }}</p>
                <div class="flex justify-end gap-2">
                  <button type="button" class="btn btn-ghost btn-sm" @click="closeExpandedRow">
                    {{ t('material.cancel') }}
                  </button>
                  <button
                    type="submit"
                    class="btn btn-primary btn-sm"
                    :disabled="createMutation.isPending.value"
                  >
                    {{ t('material.stockLotAdd') }}
                  </button>
                </div>
              </form>
            </template>
          </ExpandableRow>

          <template v-for="group in lotGroups" :key="group.materialTypeId">
            <li class="pt-4 pb-1 text-sm font-semibold text-base-content/80">
              {{ group.label }}
            </li>
            <ExpandableRow
              v-for="lot in group.lots"
              :key="lot.id"
              :expanded="expandedKey === lot.id"
              @toggle="toggleLotRow(lot.id)"
            >
              <template #summary>
                <div class="flex flex-wrap items-center gap-3">
                  <PhotoThumbnail :photo-id="lot.coverPhotoId" />
                  <div class="flex flex-1 flex-wrap items-baseline justify-between gap-2">
                  <span class="font-medium">
                    {{ lot.label?.trim() || t('material.stockLotUnlabeled') }}
                  </span>
                  <span class="text-sm text-base-content/70">{{ lotSummaryMeta(lot) }}</span>
                  </div>
                </div>
              </template>
              <template #editor>
                <form class="space-y-3" @submit.prevent="updateMutation.mutate(lot.id)">
                  <p class="text-sm">
                    <span class="text-xs opacity-80">{{ t('material.filterMaterialType') }}: </span>
                    {{ lot.materialTypeName }}
                  </p>
                  <label class="flex min-w-0 flex-col gap-1">
                    <span class="text-xs opacity-80">{{ t('material.stockLotLabel') }}</span>
                    <input
                      v-if="drafts[lot.id]"
                      v-model="drafts[lot.id].label"
                      type="text"
                      class="input input-bordered w-full"
                      :placeholder="t('material.stockLotLabelPlaceholder')"
                    />
                  </label>
                  <VariantAxisSelects
                    v-if="drafts[lot.id] && lot.variants.length"
                    v-model="drafts[lot.id].variant"
                    :axes="lot.variants"
                    optional
                  />
                  <label class="flex min-w-0 flex-col gap-1">
                    <span class="text-xs opacity-80">{{ t('material.stockQuantity') }}</span>
                    <input
                      v-if="drafts[lot.id]"
                      v-model.number="drafts[lot.id].quantity"
                      type="number"
                      min="0"
                      step="1"
                      class="input input-bordered w-full"
                      required
                    />
                  </label>
                  <div>
                    <h3 class="mb-2 text-sm font-semibold">{{ t('photos.heading') }}</h3>
                    <PhotoGallery
                      :owner="{
                        kind: 'stockLot',
                        inventoryId: props.inventoryId,
                        lotId: lot.id,
                      }"
                      :photos="lot.photos ?? []"
                      @change="() => queryClient.invalidateQueries({ queryKey: stocksQueryKey })"
                    />
                  </div>
                  <p v-if="formError && expandedKey === lot.id" class="text-sm text-error">
                    {{ formError }}
                  </p>
                  <div class="flex flex-wrap justify-end gap-2">
                    <button
                      type="button"
                      class="btn btn-ghost btn-sm"
                      :disabled="deleteMutation.isPending.value"
                      @click="deleteMutation.mutate(lot.id)"
                    >
                      {{ t('material.stockLotRemove') }}
                    </button>
                    <button
                      type="submit"
                      class="btn btn-primary btn-sm"
                      :disabled="updateMutation.isPending.value || !lotDirty(lot.id)"
                    >
                      {{ t('material.save') }}
                    </button>
                  </div>
                </form>
              </template>
            </ExpandableRow>
          </template>

          <li
            v-if="!filteredLots.length && expandedKey !== NEW_LOT"
            class="py-2 text-sm opacity-70"
          >
            {{ t('material.stockLotsEmpty') }}
          </li>
        </ul>
      </template>
    </div>
  </div>
</template>
