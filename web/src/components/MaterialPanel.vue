<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  createPiece,
  createPiecesBatch,
  createStockLot,
  fetchMaterialTypes,
  fetchPieces,
  fetchStocks,
} from '../api/material'
import { fetchSets } from '../api/sets'
import { useApiErrorMessage } from '../composables/useApiErrorMessage'
import { useInventoryQueryKey } from '../composables/useInventoryQueryKey'
import VariantAxisSelects from './VariantAxisSelects.vue'
import MaterialDataTable from './material/MaterialDataTable.vue'
import MaterialItemMetadataFields from './material/MaterialItemMetadataFields.vue'
import StockQuantityInput from './material/StockQuantityInput.vue'
import {
  materialRowsFromPiecesAndLots,
  matchesMaterialStatusFilter,
  type MaterialStatusFilter,
  type StockLotListItem,
} from './material/materialTableSetup'
import {
  emptyItemMetadataDraft,
  itemMetadataToWritePayload,
} from '../utils/materialItemValue'
import {
  batchPlaceholderKindFromPattern,
  batchPlaceholderToken,
  pieceNamesFromPattern,
  stripBatchPlaceholders,
  type BatchNamePlaceholderKind,
} from '../utils/batchNamePattern'
import { ChevronDownIcon } from '@heroicons/vue/24/outline'
import { emptyVariantMap } from '../utils/variantDisplay'

const NEW_ROW = 'new' as const
const BATCH_ROW = 'batch' as const
const NEW_LOT = 'newLot' as const
type ExpandedKey = typeof NEW_ROW | typeof BATCH_ROW | typeof NEW_LOT | null

const props = defineProps<{ inventoryId: number; canManage?: boolean }>()

const route = useRoute()
const { t } = useI18n()
const { messageFor } = useApiErrorMessage()
const queryClient = useQueryClient()

const expandedKey = ref<ExpandedKey>(null)
const formError = ref<string | null>(null)
const statusFilter = ref<MaterialStatusFilter>('active')
const newPieceMeta = ref(emptyItemMetadataDraft())
const batchMeta = ref(emptyItemMetadataDraft())
const newLotMeta = ref(emptyItemMetadataDraft())

const materialTypeId = ref<string>('')
const pieceName = ref('')
const variant = ref<Record<string, string>>({})

const batchMaterialTypeId = ref<string>('')
const batchCount = ref<number | ''>('')
const batchNamePattern = ref('')
const batchVariant = ref<Record<string, string>>({})
const batchSetMode = ref<'none' | 'existing' | 'new'>('none')
const batchSetId = ref<string>('')
const batchNewSetName = ref('')
const batchNewSetShortName = ref('')
const namePatternTouched = ref(false)
const batchPlaceholderKind = ref<BatchNamePlaceholderKind>('number')

const materialTypesQueryKey = useInventoryQueryKey('materialTypes', () => props.inventoryId)
const piecesQueryKey = useInventoryQueryKey('pieces', () => props.inventoryId)
const stocksQueryKey = useInventoryQueryKey('stocks', () => props.inventoryId)
const setsQueryKey = useInventoryQueryKey('sets', () => props.inventoryId)

const newLot = reactive({
  materialTypeId: '',
  label: '',
  variant: {} as Record<string, string>,
  quantity: 1,
})

const { data: types } = useQuery({
  queryKey: materialTypesQueryKey,
  queryFn: () => fetchMaterialTypes(props.inventoryId),
})

const { data: sets } = useQuery({
  queryKey: setsQueryKey,
  queryFn: () => fetchSets(props.inventoryId),
})

const { data: pieces, isLoading: piecesLoading } = useQuery({
  queryKey: piecesQueryKey,
  queryFn: () => fetchPieces(props.inventoryId),
})

const { data: stocks, isLoading: stocksLoading } = useQuery({
  queryKey: stocksQueryKey,
  queryFn: () => fetchStocks(props.inventoryId),
})

const isLoading = computed(() => piecesLoading.value || stocksLoading.value)

const pieceTypes = computed(() =>
  (types.value ?? []).filter((mt) => mt.tracking === 'piece'),
)

const stockTypes = computed(() => stocks.value ?? [])

const canAddPieces = computed(() => pieceTypes.value.length > 0)
const canAddLots = computed(() => stockTypes.value.length > 0)

const stockLots = computed((): StockLotListItem[] =>
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

const materialRows = computed(() => {
  const filteredPieces = (pieces.value ?? []).filter((piece) =>
    matchesMaterialStatusFilter(piece.status, statusFilter.value),
  )
  const filteredLots = stockLots.value.filter((lot) =>
    matchesMaterialStatusFilter(lot.status, statusFilter.value),
  )
  return materialRowsFromPiecesAndLots(filteredPieces, filteredLots)
})

const hasAnyMaterial = computed(() => materialRows.value.length > 0)

const selectedNewStockType = computed(() =>
  stockTypes.value.find((row) => String(row.materialTypeId) === newLot.materialTypeId),
)

const newTypeAxes = computed(() => selectedNewStockType.value?.variants ?? [])

function lotVariantPayload(map: Record<string, string>): Record<string, string> {
  const payload: Record<string, string> = {}
  for (const [label, value] of Object.entries(map)) {
    const trimmed = value?.trim()
    if (trimmed) payload[label] = trimmed
  }
  return payload
}

function resetNewLotDraft() {
  newLot.materialTypeId = stockTypes.value[0] ? String(stockTypes.value[0].materialTypeId) : ''
  newLot.label = ''
  newLot.variant = emptyVariantMap(newTypeAxes.value)
  newLot.quantity = 1
  newLotMeta.value = emptyItemMetadataDraft()
}

const selectedType = computed(() =>
  pieceTypes.value.find((mt) => String(mt.id) === materialTypeId.value),
)

const selectedTypeAxes = computed(() => selectedType.value?.variants ?? [])

const batchSelectedType = computed(() =>
  pieceTypes.value.find((mt) => String(mt.id) === batchMaterialTypeId.value),
)

const batchTypeAxes = computed(() => batchSelectedType.value?.variants ?? [])

function variantPayload(axes: { label: string; values: string[] }[], map: Record<string, string>) {
  if (!axes.length) return undefined
  const payload: Record<string, string> = {}
  for (const axis of axes) {
    const value = map[axis.label]?.trim()
    if (value) payload[axis.label] = value
  }
  return payload
}

function batchSetShortName(): string | null {
  if (batchSetMode.value === 'existing' && batchSetId.value) {
    const set = sets.value?.find((s) => String(s.id) === batchSetId.value)
    return set?.shortName?.trim() || null
  }
  if (batchSetMode.value === 'new') {
    const trimmed = batchNewSetShortName.value.trim()
    return trimmed || null
  }
  return null
}

const selectedBatchPlaceholderToken = computed(() =>
  batchPlaceholderToken(batchPlaceholderKind.value),
)

function insertBatchPlaceholder() {
  namePatternTouched.value = true
  const token = selectedBatchPlaceholderToken.value
  const stripped = stripBatchPlaceholders(batchNamePattern.value)
  batchNamePattern.value = stripped.trim() ? `${stripped}${token}` : `J3-${token}`
}

function applyBatchNamePatternExample() {
  namePatternTouched.value = true
  batchNamePattern.value = `J3-${selectedBatchPlaceholderToken.value}`
}

watch(batchNamePattern, (pattern) => {
  const kind = batchPlaceholderKindFromPattern(pattern)
  if (kind) batchPlaceholderKind.value = kind
})

function parseBatchCount(raw: number | ''): number | null {
  if (raw === '') return null
  const n = Math.floor(Number(raw))
  if (!Number.isFinite(n) || n < 1) return null
  return Math.min(n, 24)
}

const batchPreviewNames = computed(() => {
  const count = parseBatchCount(batchCount.value)
  if (count === null) return []
  return pieceNamesFromPattern(batchNamePattern.value, count)
})

const batchPreviewInline = computed(() => {
  const names = batchPreviewNames.value
  if (!names.length) return null
  if (names.length <= 3) return names.join(', ')
  return `${names[0]}, ${names[1]}, … ${names[names.length - 1]}`
})

function applyBatchNamePatternFromSet() {
  if (namePatternTouched.value) return
  const slug = batchSetShortName()
  batchNamePattern.value = slug ?? ''
}

watch(
  [batchSetMode, batchSetId, batchNewSetShortName, sets],
  () => applyBatchNamePatternFromSet(),
  { deep: true },
)

watch(materialTypeId, () => {
  variant.value = emptyVariantMap(selectedTypeAxes.value)
})

watch(batchMaterialTypeId, () => {
  batchVariant.value = emptyVariantMap(batchTypeAxes.value)
})

function resetCreateDraft() {
  pieceName.value = ''
  variant.value = emptyVariantMap(selectedTypeAxes.value)
  materialTypeId.value = pieceTypes.value[0] ? String(pieceTypes.value[0].id) : ''
  newPieceMeta.value = emptyItemMetadataDraft()
}

function resetBatchDraft() {
  batchMaterialTypeId.value = pieceTypes.value[0] ? String(pieceTypes.value[0].id) : ''
  batchCount.value = ''
  batchNamePattern.value = ''
  batchVariant.value = emptyVariantMap(batchTypeAxes.value)
  batchSetMode.value = 'none'
  batchSetId.value = ''
  batchNewSetName.value = ''
  batchNewSetShortName.value = ''
  namePatternTouched.value = false
  batchPlaceholderKind.value = 'number'
  batchMeta.value = emptyItemMetadataDraft()
}

function openNewRow() {
  if (!canAddPieces.value) return
  expandedKey.value = NEW_ROW
  resetCreateDraft()
  formError.value = null
}

function openBatchRow() {
  if (!canAddPieces.value) return
  expandedKey.value = BATCH_ROW
  resetBatchDraft()
  formError.value = null
}

watch(
  () => route.query.openCreate,
  (value) => {
    if (!props.canManage) return
    if (value === 'piece') openNewRow()
    if (value === 'batch') openBatchRow()
  },
  { immediate: true },
)

function openNewLotRow() {
  if (!canAddLots.value) return
  expandedKey.value = NEW_LOT
  resetNewLotDraft()
  formError.value = null
}

function onCreateMenuSelect(kind: typeof NEW_ROW | typeof BATCH_ROW | typeof NEW_LOT) {
  if (kind === NEW_ROW) {
    expandedKey.value === NEW_ROW ? closeExpandedRow() : openNewRow()
  } else if (kind === BATCH_ROW) {
    expandedKey.value === BATCH_ROW ? closeExpandedRow() : openBatchRow()
  } else {
    expandedKey.value === NEW_LOT ? closeExpandedRow() : openNewLotRow()
  }
  ;(document.activeElement as HTMLElement | null)?.blur()
}

function closeExpandedRow() {
  expandedKey.value = null
  formError.value = null
}

watch(
  () => newLot.materialTypeId,
  () => {
    newLot.variant = emptyVariantMap(newTypeAxes.value)
  },
)

const createMutation = useMutation({
  mutationFn: () => {
    if (!materialTypeId.value) throw new Error('missing type')
    return createPiece(props.inventoryId, {
      materialTypeId: Number(materialTypeId.value),
      name: pieceName.value,
      variant: variantPayload(selectedTypeAxes.value, variant.value),
      ...itemMetadataToWritePayload(newPieceMeta.value, { create: true }),
    })
  },
  onSuccess: async () => {
    expandedKey.value = null
    formError.value = null
    resetCreateDraft()
    await queryClient.invalidateQueries({ queryKey: ['pieces', props.inventoryId] })
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
})

const batchMutation = useMutation({
  mutationFn: () => {
    if (!batchMaterialTypeId.value) throw new Error('missing type')
    const count = parseBatchCount(batchCount.value)
    if (count === null) throw new Error('missing count')
    const payload = {
      materialTypeId: Number(batchMaterialTypeId.value),
      count,
      namePattern: batchNamePattern.value,
      variant: variantPayload(batchTypeAxes.value, batchVariant.value),
      ...itemMetadataToWritePayload(batchMeta.value, { create: true }),
    }
    if (batchSetMode.value === 'existing' && batchSetId.value) {
      return createPiecesBatch(props.inventoryId, {
        ...payload,
        setId: Number(batchSetId.value),
      })
    }
    if (batchSetMode.value === 'new' && batchNewSetName.value.trim()) {
      return createPiecesBatch(props.inventoryId, {
        ...payload,
        setName: batchNewSetName.value.trim(),
        setShortName: batchNewSetShortName.value.trim() || null,
      })
    }
    return createPiecesBatch(props.inventoryId, payload)
  },
  onSuccess: async () => {
    expandedKey.value = null
    formError.value = null
    resetBatchDraft()
    await queryClient.invalidateQueries({ queryKey: ['pieces', props.inventoryId] })
    await queryClient.invalidateQueries({ queryKey: ['sets', props.inventoryId] })
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
})

const createLotMutation = useMutation({
  mutationFn: () =>
    createStockLot(props.inventoryId, Number(newLot.materialTypeId), {
      label: newLot.label.trim() || null,
      variant: lotVariantPayload(newLot.variant),
      quantity: newLot.quantity,
      ...itemMetadataToWritePayload(newLotMeta.value, { create: true }),
    }),
  onSuccess: async () => {
    expandedKey.value = null
    formError.value = null
    resetNewLotDraft()
    await queryClient.invalidateQueries({ queryKey: [...stocksQueryKey.value] })
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
})
</script>

<template>
  <div class="flex flex-col gap-4 text-left">
      <div class="app-section-header flex flex-wrap items-center justify-between gap-2 gap-y-1">
        <h2 class="app-page-title shrink-0">{{ t('material.materialHeading') }}</h2>
        <div
          v-if="canManage && !isLoading && (canAddPieces || canAddLots)"
          class="dropdown dropdown-end"
        >
          <button
            type="button"
            tabindex="0"
            class="btn btn-ghost btn-sm gap-1"
            :aria-expanded="expandedKey !== null"
            :aria-haspopup="true"
          >
            {{ t('material.createMenu') }}
            <ChevronDownIcon class="size-4 opacity-70" aria-hidden="true" />
          </button>
          <ul
            tabindex="0"
            class="dropdown-content menu menu-sm z-20 mt-1 w-56 rounded-box border border-base-200 bg-base-100 p-1 shadow-lg"
            role="menu"
          >
            <li v-if="canAddPieces" role="none">
              <button type="button" role="menuitem" @click="onCreateMenuSelect(NEW_ROW)">
                {{ t('material.pieceNew') }}
              </button>
            </li>
            <li v-if="canAddPieces" role="none">
              <button type="button" role="menuitem" @click="onCreateMenuSelect(BATCH_ROW)">
                {{ t('material.pieceBatchNew') }}
              </button>
            </li>
            <li v-if="canAddLots" role="none">
              <button type="button" role="menuitem" @click="onCreateMenuSelect(NEW_LOT)">
                {{ t('material.stockLotMenu') }}
              </button>
            </li>
          </ul>
        </div>
      </div>

      <section
        v-if="expandedKey === NEW_ROW"
        class="rounded-lg border border-base-200 bg-base-200/30 p-3 sm:p-4"
      >
        <h3 class="mb-3 text-sm font-semibold">{{ t('material.pieceNew') }}</h3>
        <form class="space-y-3" @submit.prevent="createMutation.mutate()">
          <label class="flex min-w-0 flex-col gap-1">
            <span class="text-xs opacity-80">{{ t('material.pieceName') }}</span>
            <input
              v-model="pieceName"
              type="text"
              class="input input-bordered input-sm w-full"
              required
            />
          </label>
          <label class="flex min-w-0 max-w-md flex-col gap-1">
            <span class="text-xs opacity-80">{{ t('material.pieceType') }}</span>
            <select v-model="materialTypeId" class="select select-bordered select-sm w-full" required>
              <option v-for="mt in pieceTypes" :key="mt.id" :value="String(mt.id)">
                {{ mt.name }}
              </option>
            </select>
          </label>
          <VariantAxisSelects
            v-if="selectedTypeAxes.length"
            v-model="variant"
            :axes="selectedTypeAxes"
            compact
          />
          <MaterialItemMetadataFields
            v-model:acquired-year="newPieceMeta.acquiredYear"
            v-model:note="newPieceMeta.note"
            v-model:source="newPieceMeta.source"
            v-model:serial-number="newPieceMeta.serialNumber"
            v-model:new-value-euro="newPieceMeta.newValueEuro"
          />
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
              {{ t('material.pieceCreate') }}
            </button>
          </div>
        </form>
      </section>

      <section
        v-if="expandedKey === BATCH_ROW"
        class="rounded-lg border border-base-200 bg-base-200/30 p-3 sm:p-4"
      >
        <h3 class="mb-3 text-sm font-semibold">{{ t('material.pieceBatchHeading') }}</h3>
        <form class="space-y-3" @submit.prevent="batchMutation.mutate()">
          <label class="flex min-w-0 max-w-md flex-col gap-1">
            <span class="text-xs opacity-80">{{ t('material.pieceType') }}</span>
            <select
              v-model="batchMaterialTypeId"
              class="select select-bordered select-sm w-full"
              required
            >
              <option v-for="mt in pieceTypes" :key="mt.id" :value="String(mt.id)">
                {{ mt.name }}
              </option>
            </select>
          </label>
          <VariantAxisSelects
            v-if="batchTypeAxes.length"
            v-model="batchVariant"
            :axes="batchTypeAxes"
            compact
          />
          <fieldset class="rounded-lg border border-base-200 px-2.5 py-2">
            <legend class="px-1 text-xs font-medium opacity-80">
              {{ t('material.pieceBatchSetLegend') }}
            </legend>
            <div class="flex flex-wrap items-center gap-x-4 gap-y-1 pt-0.5">
              <label class="flex cursor-pointer items-center gap-1.5">
                <input v-model="batchSetMode" type="radio" class="radio radio-xs" value="none" />
                <span class="text-xs">{{ t('material.pieceBatchSetNone') }}</span>
              </label>
              <label class="flex cursor-pointer items-center gap-1.5">
                <input
                  v-model="batchSetMode"
                  type="radio"
                  class="radio radio-xs"
                  value="existing"
                />
                <span class="text-xs">{{ t('material.pieceBatchSetExisting') }}</span>
              </label>
              <label class="flex cursor-pointer items-center gap-1.5">
                <input v-model="batchSetMode" type="radio" class="radio radio-xs" value="new" />
                <span class="text-xs">{{ t('material.pieceBatchSetNew') }}</span>
              </label>
            </div>
            <select
              v-if="batchSetMode === 'existing'"
              v-model="batchSetId"
              class="select select-bordered select-sm mt-1.5 w-full sm:max-w-md"
              required
            >
              <option disabled value="">{{ t('material.pieceBatchPickSet') }}</option>
              <option v-for="set in sets ?? []" :key="set.id" :value="String(set.id)">
                {{ set.shortName ? `${set.shortName} · ` : '' }}{{ set.name }}
              </option>
            </select>
            <div
              v-if="batchSetMode === 'new'"
              class="mt-1.5 grid grid-cols-1 gap-1.5 sm:grid-cols-[6.5rem_minmax(0,1fr)]"
            >
              <input
                v-model="batchNewSetShortName"
                type="text"
                class="input input-bordered input-sm w-full"
                :placeholder="t('sets.shortNameOptional')"
              />
              <input
                v-model="batchNewSetName"
                type="text"
                class="input input-bordered input-sm w-full min-w-0"
                :placeholder="t('sets.newName')"
                required
              />
            </div>
          </fieldset>
          <div class="flex flex-col gap-2">
            <div class="flex flex-wrap items-end gap-2">
              <label class="flex w-full min-w-0 flex-col gap-1 sm:w-24">
                <span class="text-xs opacity-80">{{ t('material.pieceBatchCount') }}</span>
                <input
                  v-model.number="batchCount"
                  type="number"
                  min="1"
                  max="24"
                  class="input input-bordered input-sm w-full"
                  :placeholder="t('material.pieceBatchCountPlaceholder')"
                  required
                />
              </label>
              <div class="flex min-w-0 flex-1 flex-col gap-1">
                <span class="text-xs opacity-80">{{ t('material.pieceBatchNamePattern') }}</span>
                <div class="flex flex-wrap items-center gap-2">
                  <input
                    v-model="batchNamePattern"
                    type="text"
                    class="input input-bordered input-sm min-w-0 flex-1"
                    :placeholder="
                      t('material.pieceBatchNamePatternHint', {
                        placeholder: selectedBatchPlaceholderToken,
                      })
                    "
                    required
                    @input="namePatternTouched = true"
                  />
                  <select
                    v-model="batchPlaceholderKind"
                    class="select select-bordered select-sm w-auto max-w-[11rem] shrink-0"
                    :aria-label="t('material.pieceBatchPlaceholderKind')"
                  >
                    <option value="number">
                      {{ t('material.pieceBatchPlaceholderNumber', { placeholder: '{n}' }) }}
                    </option>
                    <option value="letter">
                      {{ t('material.pieceBatchPlaceholderLetter', { placeholder: '{a}' }) }}
                    </option>
                    <option value="letterUpper">
                      {{ t('material.pieceBatchPlaceholderLetterUpper', { placeholder: '{A}' }) }}
                    </option>
                    <option value="roman">
                      {{ t('material.pieceBatchPlaceholderRoman', { placeholder: '{r}' }) }}
                    </option>
                    <option value="romanUpper">
                      {{ t('material.pieceBatchPlaceholderRomanUpper', { placeholder: '{R}' }) }}
                    </option>
                  </select>
                  <button
                    type="button"
                    class="btn btn-ghost btn-sm shrink-0"
                    @click="insertBatchPlaceholder"
                  >
                    {{ t('material.pieceBatchInsertPlaceholder') }}
                  </button>
                </div>
              </div>
            </div>
            <p class="text-xs opacity-70">{{ t('material.pieceBatchNamePatternHelp') }}</p>
          </div>
          <p v-if="batchPreviewInline" class="text-xs opacity-65">
            <span class="opacity-80">{{ t('material.pieceBatchNamePreview') }}:</span>
            {{ batchPreviewInline }}
          </p>
          <div
            v-else-if="batchNamePattern.trim()"
            class="rounded-lg border border-warning/50 bg-warning/10 px-3 py-2 text-sm"
          >
            <p class="text-xs">{{ t('material.pieceBatchNamePatternMissingPlaceholder') }}</p>
            <button
              type="button"
              class="btn btn-ghost btn-xs mt-2"
              @click="applyBatchNamePatternExample"
            >
              {{ t('material.pieceBatchUseExample') }}
            </button>
          </div>
          <MaterialItemMetadataFields
            v-model:acquired-year="batchMeta.acquiredYear"
            v-model:note="batchMeta.note"
            v-model:source="batchMeta.source"
            v-model:serial-number="batchMeta.serialNumber"
            v-model:new-value-euro="batchMeta.newValueEuro"
          />
          <p v-if="formError" class="text-sm text-error">{{ formError }}</p>
          <div class="flex justify-end gap-2">
            <button type="button" class="btn btn-ghost btn-sm" @click="closeExpandedRow">
              {{ t('material.cancel') }}
            </button>
            <button
              type="submit"
              class="btn btn-primary btn-sm"
              :disabled="batchMutation.isPending.value"
            >
              {{ t('material.pieceBatchCreate') }}
            </button>
          </div>
        </form>
      </section>

      <section
        v-if="expandedKey === NEW_LOT"
        class="rounded-lg border border-base-200 bg-base-200/30 p-3 sm:p-4"
      >
        <h3 class="mb-3 text-sm font-semibold">{{ t('material.stockLotAdd') }}</h3>
        <form class="space-y-3" @submit.prevent="createLotMutation.mutate()">
          <label class="flex min-w-0 flex-col gap-1">
            <span class="text-xs opacity-80">{{ t('material.stockLotLabel') }}</span>
            <input
              v-model="newLot.label"
              type="text"
              class="input input-bordered input-sm w-full"
              :placeholder="t('material.stockLotLabelPlaceholder')"
            />
          </label>
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <label class="flex min-w-0 flex-col gap-1">
              <span class="text-xs opacity-80">{{ t('material.filterMaterialType') }}</span>
              <select
                v-model="newLot.materialTypeId"
                class="select select-bordered select-sm w-full"
                required
              >
                <option
                  v-for="row in stockTypes"
                  :key="row.materialTypeId"
                  :value="String(row.materialTypeId)"
                >
                  {{ row.materialTypeName }}
                </option>
              </select>
            </label>
            <label class="flex min-w-0 flex-col gap-1">
              <span class="text-xs opacity-80">{{ t('material.stockQuantity') }}</span>
              <StockQuantityInput
                v-model="newLot.quantity"
                :unit="selectedNewStockType?.unit"
                compact
              />
            </label>
            <VariantAxisSelects
              v-if="newTypeAxes.length"
              v-model="newLot.variant"
              :axes="newTypeAxes"
              compact
              inline
            />
          </div>
          <MaterialItemMetadataFields
            v-model:acquired-year="newLotMeta.acquiredYear"
            v-model:note="newLotMeta.note"
            v-model:source="newLotMeta.source"
            v-model:serial-number="newLotMeta.serialNumber"
            v-model:new-value-euro="newLotMeta.newValueEuro"
          />
          <p v-if="formError" class="text-sm text-error">{{ formError }}</p>
          <div class="flex justify-end gap-2">
            <button type="button" class="btn btn-ghost btn-sm" @click="closeExpandedRow">
              {{ t('material.cancel') }}
            </button>
            <button
              type="submit"
              class="btn btn-primary btn-sm"
              :disabled="createLotMutation.isPending.value"
            >
              {{ t('material.stockLotAdd') }}
            </button>
          </div>
        </form>
      </section>

      <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>
      <template v-else>
        <p v-if="!canAddPieces && !canAddLots" class="text-sm opacity-70">
          {{ t('material.materialNeedTypes') }}
        </p>
        <p v-else-if="!hasAnyMaterial" class="text-sm opacity-70">{{ t('material.empty') }}</p>
        <MaterialDataTable
          v-else
          :inventory-id="inventoryId"
          :rows="materialRows"
          :material-types="types ?? []"
          :status-filter="statusFilter"
          @update:status-filter="statusFilter = $event"
        />
      </template>
  </div>
</template>
