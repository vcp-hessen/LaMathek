<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  createPiece,
  createPiecesBatch,
  fetchMaterialTypes,
  fetchPieces,
} from '../api/material'
import type { Piece } from '../schemas/material'
import { fetchSets } from '../api/sets'
import { useApiErrorMessage } from '../composables/useApiErrorMessage'
import { useInventoryQueryKey } from '../composables/useInventoryQueryKey'
import PhotoThumbnail from './PhotoThumbnail.vue'
import VariantAxisSelects from './VariantAxisSelects.vue'
import {
  batchPlaceholderKindFromPattern,
  batchPlaceholderToken,
  pieceNamesFromPattern,
  stripBatchPlaceholders,
  type BatchNamePlaceholderKind,
} from '../utils/batchNamePattern'
import {
  buildVariantAxisCatalog,
  pieceMatchesVariantFilters,
  variantFiltersAreActive,
} from '../utils/pieceVariantFilters'
import {
  emptyVariantMap,
  variantMapSummary,
} from '../utils/variantDisplay'

const NEW_ROW = 'new' as const
const BATCH_ROW = 'batch' as const
type ExpandedKey = typeof NEW_ROW | typeof BATCH_ROW | null

const PAGE_SIZE_OPTIONS = [25, 50, 100] as const

const props = defineProps<{ inventoryId: number }>()

const { t } = useI18n()
const router = useRouter()
const { messageFor } = useApiErrorMessage()
const queryClient = useQueryClient()

const expandedKey = ref<ExpandedKey>(null)
const formError = ref<string | null>(null)
const filterMaterialTypeId = ref<string>('')
const variantFilterAxes = ref<string[]>([])
const variantFilterValues = ref<Record<string, string[]>>({})
const variantFilterAxisToAdd = ref('')
const searchQuery = ref('')
const page = ref(1)
const pageSize = ref<number>(PAGE_SIZE_OPTIONS[0])

type SortKey = 'name' | 'materialTypeName'
const sortKey = ref<SortKey>('name')
const sortAsc = ref(true)

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
const setsQueryKey = useInventoryQueryKey('sets', () => props.inventoryId)

const { data: types } = useQuery({
  queryKey: materialTypesQueryKey,
  queryFn: () => fetchMaterialTypes(props.inventoryId),
})

const { data: sets } = useQuery({
  queryKey: setsQueryKey,
  queryFn: () => fetchSets(props.inventoryId),
})

const { data: pieces, isLoading } = useQuery({
  queryKey: piecesQueryKey,
  queryFn: () => fetchPieces(props.inventoryId),
})

const pieceTypes = computed(() =>
  (types.value ?? []).filter((mt) => mt.tracking === 'piece'),
)

const variantAxisCatalog = computed(() => buildVariantAxisCatalog(pieceTypes.value))

const addableVariantAxes = computed(() =>
  variantAxisCatalog.value.filter((entry) => !variantFilterAxes.value.includes(entry.label)),
)

const materialTypeById = computed(() => {
  const map = new Map<number, (typeof pieceTypes.value)[number]>()
  for (const mt of pieceTypes.value) map.set(mt.id, mt)
  return map
})

const canAddPieces = computed(() => pieceTypes.value.length > 0)

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

function pieceVariantSummary(piece: Piece): string {
  const mt = types.value?.find((row) => row.id === piece.materialTypeId)
  return mt ? variantMapSummary(mt.variants, piece.variant) : ''
}

function pieceMatchesSearch(piece: Piece, query: string): boolean {
  const variantText = pieceVariantSummary(piece)
  const haystack = [
    piece.name,
    piece.materialTypeName,
    variantText,
    piece.setName ?? '',
  ]
    .join(' ')
    .toLowerCase()
  return haystack.includes(query)
}

const filteredPieces = computed(() => {
  let list = pieces.value ?? []
  if (filterMaterialTypeId.value) {
    const id = Number(filterMaterialTypeId.value)
    list = list.filter((p) => p.materialTypeId === id)
  }
  const query = searchQuery.value.trim().toLowerCase()
  if (query) {
    list = list.filter((p) => pieceMatchesSearch(p, query))
  }
  if (variantFiltersAreActive(variantFilterValues.value)) {
    list = list.filter((p) =>
      pieceMatchesVariantFilters(
        p,
        materialTypeById.value.get(p.materialTypeId),
        variantFilterValues.value,
      ),
    )
  }
  return list
})

const sortedPieces = computed(() => {
  const list = [...filteredPieces.value]
  const dir = sortAsc.value ? 1 : -1
  list.sort((a, b) => {
    const av = a[sortKey.value]
    const bv = b[sortKey.value]
    return av.localeCompare(bv, 'de') * dir
  })
  return list
})

const pageCount = computed(() =>
  Math.max(1, Math.ceil(sortedPieces.value.length / pageSize.value)),
)

const currentPage = computed(() => Math.min(page.value, pageCount.value))

const pagePieces = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return sortedPieces.value.slice(start, start + pageSize.value)
})

const pageFrom = computed(() =>
  sortedPieces.value.length === 0 ? 0 : (currentPage.value - 1) * pageSize.value + 1,
)

const pageTo = computed(() =>
  Math.min(currentPage.value * pageSize.value, sortedPieces.value.length),
)

const totalPieceCount = computed(() => (pieces.value ?? []).length)

const hasActiveFilter = computed(
  () =>
    !!filterMaterialTypeId.value ||
    !!searchQuery.value.trim() ||
    variantFiltersAreActive(variantFilterValues.value),
)

watch([searchQuery, filterMaterialTypeId, pageSize], () => {
  page.value = 1
})

watch(
  [variantFilterAxes, variantFilterValues],
  () => {
    page.value = 1
  },
  { deep: true },
)

function catalogValuesForLabel(label: string): string[] {
  return variantAxisCatalog.value.find((entry) => entry.label === label)?.values ?? []
}

function isVariantValueChecked(label: string, value: string): boolean {
  return variantFilterValues.value[label]?.includes(value) ?? false
}

function setVariantValueChecked(label: string, value: string, checked: boolean) {
  const current = variantFilterValues.value[label] ?? []
  const nextValues = checked
    ? current.includes(value)
      ? current
      : [...current, value]
    : current.filter((v) => v !== value)
  variantFilterValues.value = { ...variantFilterValues.value, [label]: nextValues }
}

function addVariantFilterAxis() {
  const label = variantFilterAxisToAdd.value.trim()
  if (!label || variantFilterAxes.value.includes(label)) return
  variantFilterAxes.value = [...variantFilterAxes.value, label]
  if (!variantFilterValues.value[label]) {
    variantFilterValues.value = { ...variantFilterValues.value, [label]: [] }
  }
  variantFilterAxisToAdd.value = ''
}

function removeVariantFilterAxis(label: string) {
  variantFilterAxes.value = variantFilterAxes.value.filter((row) => row !== label)
  const next = { ...variantFilterValues.value }
  delete next[label]
  variantFilterValues.value = next
}

function goToPage(next: number) {
  page.value = Math.min(Math.max(1, next), pageCount.value)
}

function toggleSort(key: SortKey) {
  if (sortKey.value === key) sortAsc.value = !sortAsc.value
  else {
    sortKey.value = key
    sortAsc.value = true
  }
}

function sortIndicator(key: SortKey): string {
  if (sortKey.value !== key) return ''
  return sortAsc.value ? ' ↑' : ' ↓'
}

function pieceDetailPath(pieceId: number): string {
  return `/inventories/${props.inventoryId}/pieces/${pieceId}`
}

function goToPiece(pieceId: number) {
  void router.push(pieceDetailPath(pieceId))
}

function setLabel(piece: Piece): string {
  if (!piece.setName) return '—'
  if (piece.setRole === 'optional') {
    return `${piece.setName} (${t('sets.optionals')})`
  }
  if (piece.setRole === 'assignment') {
    return `${piece.setName} (${t('sets.assignment')})`
  }
  return piece.setName
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

function closeExpandedRow() {
  expandedKey.value = null
  formError.value = null
}

const createMutation = useMutation({
  mutationFn: () => {
    if (!materialTypeId.value) throw new Error('missing type')
    return createPiece(props.inventoryId, {
      materialTypeId: Number(materialTypeId.value),
      name: pieceName.value,
      variant: variantPayload(selectedTypeAxes.value, variant.value),
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
</script>

<template>
  <div class="card bg-base-100 shadow-md">
    <div class="card-body gap-4 text-left">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h2 class="card-title text-lg">{{ t('material.piecesHeading') }}</h2>
        <div v-if="!isLoading && canAddPieces" class="flex flex-wrap gap-1">
          <button
            type="button"
            class="btn btn-ghost btn-sm"
            :aria-expanded="expandedKey === NEW_ROW"
            @click="expandedKey === NEW_ROW ? closeExpandedRow() : openNewRow()"
          >
            {{ t('material.pieceNew') }}
          </button>
          <button
            type="button"
            class="btn btn-ghost btn-sm"
            :aria-expanded="expandedKey === BATCH_ROW"
            @click="expandedKey === BATCH_ROW ? closeExpandedRow() : openBatchRow()"
          >
            {{ t('material.pieceBatchNew') }}
          </button>
        </div>
      </div>

      <section
        v-if="expandedKey === NEW_ROW"
        class="rounded-lg border border-base-200 bg-base-200/30 p-3 sm:p-4"
      >
        <h3 class="mb-3 text-sm font-semibold">{{ t('material.pieceNew') }}</h3>
        <form class="space-y-3" @submit.prevent="createMutation.mutate()">
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <label class="flex min-w-0 flex-col gap-1">
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
              inline
            />
          </div>
          <label class="flex min-w-0 flex-col gap-1">
            <span class="text-xs opacity-80">{{ t('material.pieceName') }}</span>
            <input
              v-model="pieceName"
              type="text"
              class="input input-bordered input-sm w-full"
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
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <label class="flex min-w-0 flex-col gap-1">
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
              inline
            />
          </div>
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
                <option value="roman">
                  {{ t('material.pieceBatchPlaceholderRoman', { placeholder: '{r}' }) }}
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
        v-if="canAddPieces && !isLoading"
        class="rounded-lg border border-base-200 px-2.5 py-2"
      >
        <div
          class="grid grid-cols-1 gap-2 sm:grid-cols-2"
          :class="variantAxisCatalog.length ? 'lg:grid-cols-[minmax(0,1fr)_10rem_minmax(8rem,11rem)]' : ''"
        >
          <label class="flex min-w-0 flex-col gap-0.5 sm:col-span-2 lg:col-span-1">
            <span class="text-xs opacity-80">{{ t('material.piecesSearchLabel') }}</span>
            <input
              v-model="searchQuery"
              type="search"
              class="input input-bordered input-sm w-full"
              :placeholder="t('material.piecesSearchPlaceholder')"
              autocomplete="off"
            />
          </label>
          <label class="flex min-w-0 flex-col gap-0.5">
            <span class="text-xs opacity-80">{{ t('material.filterMaterialType') }}</span>
            <select v-model="filterMaterialTypeId" class="select select-bordered select-sm w-full">
              <option value="">{{ t('material.filterAllMaterialTypes') }}</option>
              <option v-for="mt in pieceTypes" :key="mt.id" :value="String(mt.id)">
                {{ mt.name }}
              </option>
            </select>
          </label>
          <label v-if="variantAxisCatalog.length" class="flex min-w-0 flex-col gap-0.5">
            <span class="text-xs opacity-80">{{ t('material.piecesVariantFilterHeading') }}</span>
            <select
              v-model="variantFilterAxisToAdd"
              class="select select-bordered select-sm w-full"
              :disabled="!addableVariantAxes.length"
              @change="addVariantFilterAxis"
            >
              <option value="">{{ t('material.piecesVariantFilterPickAxis') }}</option>
              <option v-for="entry in addableVariantAxes" :key="entry.label" :value="entry.label">
                {{ entry.label }}
              </option>
            </select>
          </label>
        </div>
        <template v-if="variantAxisCatalog.length">
          <p
            v-if="variantFilterAxes.length"
            class="mt-1.5 text-xs opacity-60"
          >
            {{ t('material.piecesVariantFilterHelp') }}
          </p>
          <div
            v-for="label in variantFilterAxes"
            :key="label"
            class="mt-2 border-t border-base-200/80 pt-2"
          >
            <div class="flex flex-wrap items-center justify-between gap-1">
              <span class="text-xs font-medium">{{ label }}</span>
              <button
                type="button"
                class="btn btn-ghost btn-xs h-auto min-h-0 px-1 py-0"
                @click="removeVariantFilterAxis(label)"
              >
                {{ t('material.piecesVariantFilterRemove', { label }) }}
              </button>
            </div>
            <div class="mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
              <label
                v-for="value in catalogValuesForLabel(label)"
                :key="value"
                class="flex cursor-pointer items-center gap-1 text-xs"
              >
                <input
                  type="checkbox"
                  class="checkbox checkbox-xs"
                  :checked="isVariantValueChecked(label, value)"
                  @change="
                    setVariantValueChecked(
                      label,
                      value,
                      ($event.target as HTMLInputElement).checked,
                    )
                  "
                />
                <span>{{ value }}</span>
              </label>
            </div>
          </div>
        </template>
      </section>

      <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>
      <template v-else>
        <p v-if="!canAddPieces" class="text-sm opacity-70">{{ t('material.piecesNeedType') }}</p>
        <template v-else>
          <p v-if="totalPieceCount === 0" class="text-sm opacity-70">
            {{ t('material.piecesEmpty') }}
          </p>
          <p v-else-if="sortedPieces.length === 0" class="text-sm opacity-70">
            {{ t('material.piecesNoSearchResults') }}
          </p>
          <template v-else>
            <div class="overflow-x-auto rounded-lg border border-base-200">
              <table class="table table-sm pieces-table">
                <thead>
                  <tr>
                    <th class="w-12 sm:table-cell">
                      <span class="sr-only">{{ t('material.piecesTablePhoto') }}</span>
                    </th>
                    <th>
                      <button
                        type="button"
                        class="font-semibold hover:underline"
                        @click="toggleSort('name')"
                      >
                        {{ t('material.piecesTableName') }}{{ sortIndicator('name') }}
                      </button>
                    </th>
                    <th class="hidden md:table-cell">
                      <button
                        type="button"
                        class="font-semibold hover:underline"
                        @click="toggleSort('materialTypeName')"
                      >
                        {{ t('material.piecesTableMaterialType') }}{{ sortIndicator('materialTypeName') }}
                      </button>
                    </th>
                    <th class="hidden lg:table-cell">{{ t('material.piecesTableVariant') }}</th>
                    <th class="hidden sm:table-cell">{{ t('material.piecesTableSet') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="piece in pagePieces"
                    :key="piece.id"
                    tabindex="0"
                    role="link"
                    class="cursor-pointer"
                    @click="goToPiece(piece.id)"
                    @keydown.enter.prevent="goToPiece(piece.id)"
                    @keydown.space.prevent="goToPiece(piece.id)"
                  >
                    <td class="hidden w-12 sm:table-cell">
                      <PhotoThumbnail :photo-id="piece.coverPhotoId" />
                    </td>
                    <td>
                      <span class="font-medium">{{ piece.name }}</span>
                      <span class="mt-0.5 block text-xs opacity-70 md:hidden">
                        {{ piece.materialTypeName }}
                      </span>
                    </td>
                    <td class="hidden md:table-cell">{{ piece.materialTypeName }}</td>
                    <td class="hidden max-w-[12rem] truncate lg:table-cell">
                      {{ pieceVariantSummary(piece) || '—' }}
                    </td>
                    <td class="hidden max-w-[10rem] truncate sm:table-cell">
                      {{ setLabel(piece) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="flex flex-wrap items-center justify-between gap-3">
              <p class="text-xs opacity-70">
                {{ t('material.piecesPageRange', { from: pageFrom, to: pageTo, total: sortedPieces.length }) }}
                <template v-if="hasActiveFilter && totalPieceCount !== sortedPieces.length">
                  · {{ t('material.piecesFilteredTotal', { total: totalPieceCount }) }}
                </template>
              </p>
              <div class="flex flex-wrap items-center gap-2">
                <label class="flex items-center gap-2">
                  <span class="text-xs opacity-80">{{ t('material.piecesPageSize') }}</span>
                  <select v-model.number="pageSize" class="select select-bordered select-sm w-20">
                    <option v-for="size in PAGE_SIZE_OPTIONS" :key="size" :value="size">
                      {{ size }}
                    </option>
                  </select>
                </label>
                <div class="join">
                  <button
                    type="button"
                    class="btn btn-sm join-item"
                    :disabled="currentPage <= 1"
                    :aria-label="t('material.piecesPreviousPage')"
                    @click="goToPage(currentPage - 1)"
                  >
                    ‹
                  </button>
                  <button
                    type="button"
                    class="btn btn-sm join-item"
                    :disabled="currentPage >= pageCount"
                    :aria-label="t('material.piecesNextPage')"
                    @click="goToPage(currentPage + 1)"
                  >
                    ›
                  </button>
                </div>
              </div>
            </div>
          </template>
        </template>
      </template>
    </div>
  </div>
</template>
