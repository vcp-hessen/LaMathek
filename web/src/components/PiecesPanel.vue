<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  createPiece,
  createPiecesBatch,
  deletePiece,
  fetchMaterialTypes,
  fetchPieces,
  updatePiece,
} from '../api/material'
import type { Piece } from '../schemas/material'
import { fetchMe } from '../api/me'
import { fetchSets } from '../api/sets'
import { useApiErrorMessage } from '../composables/useApiErrorMessage'
import { useInventoryQueryKey } from '../composables/useInventoryQueryKey'
import ExpandableRow from './ExpandableRow.vue'
import SuperuserDestructiveDelete from './SuperuserDestructiveDelete.vue'

const NEW_ROW = 'new' as const
const BATCH_ROW = 'batch' as const
type ExpandedKey = number | typeof NEW_ROW | typeof BATCH_ROW | null

const props = defineProps<{ inventoryId: number }>()

const { t } = useI18n()
const { messageFor } = useApiErrorMessage()
const queryClient = useQueryClient()

const expandedKey = ref<ExpandedKey>(null)
const formError = ref<string | null>(null)
const filterMaterialTypeId = ref<string>('')

const materialTypeId = ref<string>('')
const pieceName = ref('')
const variant = ref('')

const editMaterialTypeId = ref<string>('')
const editPieceName = ref('')
const editVariant = ref('')

const batchMaterialTypeId = ref<string>('')
const batchCount = ref(4)
const batchNamePattern = ref('')
const batchVariant = ref('')
const batchSetMode = ref<'none' | 'existing' | 'new'>('none')
const batchSetId = ref<string>('')
const batchNewSetName = ref('')
const batchNewSetShortName = ref('')
const namePatternTouched = ref(false)

const { data: me } = useQuery({ queryKey: ['me'], queryFn: fetchMe })

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

const canAddPieces = computed(() => pieceTypes.value.length > 0)

const selectedType = computed(() =>
  pieceTypes.value.find((mt) => String(mt.id) === materialTypeId.value),
)

const variantOptions = computed(() => selectedType.value?.variantValues ?? [])

const batchSelectedType = computed(() =>
  pieceTypes.value.find((mt) => String(mt.id) === batchMaterialTypeId.value),
)

const batchVariantOptions = computed(() => batchSelectedType.value?.variantValues ?? [])

const editSelectedType = computed(() =>
  pieceTypes.value.find((mt) => String(mt.id) === editMaterialTypeId.value),
)

const editVariantOptions = computed(() => editSelectedType.value?.variantValues ?? [])

const filteredPieces = computed(() => {
  let list = pieces.value ?? []
  if (filterMaterialTypeId.value) {
    const id = Number(filterMaterialTypeId.value)
    list = list.filter((p) => p.materialTypeId === id)
  }
  return list
})

type PieceGroup = { materialTypeId: number; label: string; pieces: Piece[] }

const pieceGroups = computed((): PieceGroup[] => {
  const byType = new Map<number, Piece[]>()
  for (const piece of filteredPieces.value) {
    const bucket = byType.get(piece.materialTypeId) ?? []
    bucket.push(piece)
    byType.set(piece.materialTypeId, bucket)
  }
  const groups: PieceGroup[] = []
  for (const [materialTypeId, groupPieces] of byType.entries()) {
    const label =
      groupPieces[0]?.materialTypeName ??
      pieceTypes.value.find((mt) => mt.id === materialTypeId)?.name ??
      ''
    groups.push({
      materialTypeId,
      label,
      pieces: [...groupPieces].sort((a, b) => a.name.localeCompare(b.name, 'de')),
    })
  }
  return groups.sort((a, b) => a.label.localeCompare(b.label, 'de'))
})

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

function pieceNamesFromPattern(pattern: string, count: number): string[] {
  const normalized = pattern.trim()
  if (!normalized.includes('{n}')) return []
  const total = Math.min(Math.max(1, Math.floor(count) || 1), 24)
  return Array.from({ length: total }, (_, index) =>
    normalized.replaceAll('{n}', String(index + 1)),
  )
}

const batchPreviewNames = computed(() =>
  pieceNamesFromPattern(batchNamePattern.value, batchCount.value),
)

const batchPreviewVisible = computed(() => {
  const names = batchPreviewNames.value
  const maxShown = 6
  if (names.length <= maxShown) {
    return { names, more: 0 }
  }
  return { names: names.slice(0, maxShown), more: names.length - maxShown }
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
  variant.value = ''
})

watch(batchMaterialTypeId, () => {
  batchVariant.value = ''
})

function resetCreateDraft() {
  pieceName.value = ''
  variant.value = ''
  materialTypeId.value = pieceTypes.value[0] ? String(pieceTypes.value[0].id) : ''
}

function resetBatchDraft() {
  batchMaterialTypeId.value = pieceTypes.value[0] ? String(pieceTypes.value[0].id) : ''
  batchCount.value = 4
  batchNamePattern.value = ''
  batchVariant.value = ''
  batchSetMode.value = 'none'
  batchSetId.value = ''
  batchNewSetName.value = ''
  batchNewSetShortName.value = ''
  namePatternTouched.value = false
}

function loadEditDraft(piece: Piece) {
  editMaterialTypeId.value = String(piece.materialTypeId)
  editPieceName.value = piece.name
  editVariant.value = piece.variant ?? ''
  formError.value = null
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

function toggleRow(id: number) {
  if (expandedKey.value === id) {
    expandedKey.value = null
    formError.value = null
    return
  }
  expandedKey.value = id
  const piece = pieces.value?.find((row) => row.id === id)
  if (piece) loadEditDraft(piece)
}

watch(editMaterialTypeId, (newId, oldId) => {
  if (oldId && newId !== oldId && typeof expandedKey.value === 'number') {
    const opts = pieceTypes.value.find((mt) => String(mt.id) === newId)?.variantValues ?? []
    if (!opts.includes(editVariant.value)) {
      editVariant.value = ''
    }
  }
})

const createMutation = useMutation({
  mutationFn: () => {
    if (!materialTypeId.value) throw new Error('missing type')
    return createPiece(props.inventoryId, {
      materialTypeId: Number(materialTypeId.value),
      name: pieceName.value,
      variant: variantOptions.value.length ? variant.value : null,
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
    const payload = {
      materialTypeId: Number(batchMaterialTypeId.value),
      count: batchCount.value,
      namePattern: batchNamePattern.value,
      variant: batchVariantOptions.value.length ? batchVariant.value || null : null,
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

const updateMutation = useMutation({
  mutationFn: (id: number) =>
    updatePiece(id, {
      name: editPieceName.value,
      materialTypeId: Number(editMaterialTypeId.value),
      variant: editVariantOptions.value.length ? editVariant.value || null : null,
    }),
  onSuccess: async () => {
    formError.value = null
    await queryClient.invalidateQueries({ queryKey: ['pieces', props.inventoryId] })
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
})

const deleteMutation = useMutation({
  mutationFn: (id: number) => deletePiece(id),
  onSuccess: async (_data, id) => {
    if (expandedKey.value === id) expandedKey.value = null
    formError.value = null
    await queryClient.invalidateQueries({ queryKey: ['pieces', props.inventoryId] })
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
})

function pieceSummaryMeta(piece: Piece): string {
  const parts: string[] = []
  if (piece.variant) parts.push(piece.variant)
  if (piece.setName) parts.push(t('sets.onSet', { name: piece.setName }))
  return parts.join(' · ')
}

watch(expandedKey, (key) => {
  if (typeof key === 'number') {
    const piece = pieces.value?.find((row) => row.id === key)
    if (piece) loadEditDraft(piece)
  }
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
            @click="openNewRow"
          >
            {{ t('material.pieceNew') }}
          </button>
          <button
            type="button"
            class="btn btn-ghost btn-sm"
            :aria-expanded="expandedKey === BATCH_ROW"
            @click="openBatchRow"
          >
            {{ t('material.pieceBatchNew') }}
          </button>
        </div>
      </div>

      <label v-if="canAddPieces && !isLoading" class="flex min-w-0 flex-col gap-1 sm:max-w-xs">
        <span class="text-xs opacity-80">{{ t('material.filterMaterialType') }}</span>
        <select v-model="filterMaterialTypeId" class="select select-bordered select-sm">
          <option value="">{{ t('material.filterAllMaterialTypes') }}</option>
          <option v-for="mt in pieceTypes" :key="mt.id" :value="String(mt.id)">
            {{ mt.name }}
          </option>
        </select>
      </label>

      <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>
      <template v-else>
        <p v-if="!canAddPieces" class="text-sm opacity-70">{{ t('material.piecesNeedType') }}</p>
        <ul class="list-none">
          <ExpandableRow
            v-if="expandedKey === NEW_ROW"
            :expanded="true"
            @toggle="closeExpandedRow"
          >
            <template #summary>
              <span class="font-medium">{{ t('material.pieceNew') }}</span>
            </template>
            <template #editor>
              <form class="space-y-3" @submit.prevent="createMutation.mutate()">
                <select v-model="materialTypeId" class="select select-bordered w-full" required>
                  <option v-for="mt in pieceTypes" :key="mt.id" :value="String(mt.id)">
                    {{ mt.name }}
                  </option>
                </select>
                <input
                  v-model="pieceName"
                  type="text"
                  class="input input-bordered w-full"
                  :placeholder="t('material.pieceName')"
                  required
                />
                <select
                  v-if="variantOptions.length"
                  v-model="variant"
                  class="select select-bordered w-full"
                  required
                >
                  <option disabled value="">{{ t('material.pieceVariant') }}</option>
                  <option v-for="v in variantOptions" :key="v" :value="v">{{ v }}</option>
                </select>
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
            </template>
          </ExpandableRow>

          <ExpandableRow
            v-if="expandedKey === BATCH_ROW"
            :expanded="true"
            @toggle="closeExpandedRow"
          >
            <template #summary>
              <span class="font-medium">{{ t('material.pieceBatchHeading') }}</span>
            </template>
            <template #editor>
              <form class="space-y-3" @submit.prevent="batchMutation.mutate()">
                <select
                  v-model="batchMaterialTypeId"
                  class="select select-bordered w-full"
                  required
                >
                  <option v-for="mt in pieceTypes" :key="mt.id" :value="String(mt.id)">
                    {{ mt.name }}
                  </option>
                </select>
                <select
                  v-if="batchVariantOptions.length"
                  v-model="batchVariant"
                  class="select select-bordered w-full"
                  required
                >
                  <option disabled value="">{{ t('material.pieceVariant') }}</option>
                  <option v-for="v in batchVariantOptions" :key="v" :value="v">{{ v }}</option>
                </select>
                <label class="flex flex-col gap-1">
                  <span class="text-xs opacity-80">{{ t('material.pieceBatchCount') }}</span>
                  <input
                    v-model.number="batchCount"
                    type="number"
                    min="1"
                    max="24"
                    class="input input-bordered"
                    required
                  />
                </label>
                <fieldset class="rounded-lg border border-base-200 px-3 py-2">
                  <legend class="px-1 text-sm">{{ t('material.pieceBatchSetLegend') }}</legend>
                  <div class="mt-2 flex flex-col gap-2">
                    <label class="flex cursor-pointer items-center gap-2">
                      <input
                        v-model="batchSetMode"
                        type="radio"
                        class="radio radio-sm"
                        value="none"
                      />
                      <span class="text-sm">{{ t('material.pieceBatchSetNone') }}</span>
                    </label>
                    <label class="flex cursor-pointer items-center gap-2">
                      <input
                        v-model="batchSetMode"
                        type="radio"
                        class="radio radio-sm"
                        value="existing"
                      />
                      <span class="text-sm">{{ t('material.pieceBatchSetExisting') }}</span>
                    </label>
                    <select
                      v-if="batchSetMode === 'existing'"
                      v-model="batchSetId"
                      class="select select-bordered select-sm"
                      required
                    >
                      <option disabled value="">{{ t('material.pieceBatchPickSet') }}</option>
                      <option v-for="set in sets ?? []" :key="set.id" :value="String(set.id)">
                        {{ set.shortName ? `${set.shortName} · ` : '' }}{{ set.name }}
                      </option>
                    </select>
                    <label class="flex cursor-pointer items-center gap-2">
                      <input
                        v-model="batchSetMode"
                        type="radio"
                        class="radio radio-sm"
                        value="new"
                      />
                      <span class="text-sm">{{ t('material.pieceBatchSetNew') }}</span>
                    </label>
                    <div v-if="batchSetMode === 'new'" class="flex flex-col gap-2 sm:flex-row">
                      <input
                        v-model="batchNewSetName"
                        type="text"
                        class="input input-bordered input-sm flex-1"
                        :placeholder="t('sets.newName')"
                        required
                      />
                      <input
                        v-model="batchNewSetShortName"
                        type="text"
                        class="input input-bordered input-sm sm:w-28"
                        :placeholder="t('sets.shortNameOptional')"
                      />
                    </div>
                  </div>
                </fieldset>
                <label class="flex flex-col gap-1">
                  <span class="text-xs opacity-80">{{ t('material.pieceBatchNamePattern') }}</span>
                  <input
                    v-model="batchNamePattern"
                    type="text"
                    class="input input-bordered"
                    :placeholder="t('material.pieceBatchNamePatternHint')"
                    required
                    @input="namePatternTouched = true"
                  />
                  <span class="text-xs opacity-70">{{ t('material.pieceBatchNamePatternHelp') }}</span>
                </label>
                <div
                  v-if="batchPreviewNames.length"
                  class="rounded-lg border border-base-200 bg-base-200/40 px-3 py-2 text-sm"
                >
                  <p class="text-xs font-medium opacity-80">{{ t('material.pieceBatchNamePreview') }}</p>
                  <ul class="mt-1 list-inside list-disc">
                    <li v-for="name in batchPreviewVisible.names" :key="name">{{ name }}</li>
                  </ul>
                  <p v-if="batchPreviewVisible.more > 0" class="mt-1 text-xs opacity-70">
                    {{ t('material.pieceBatchNamePreviewMore', { count: batchPreviewVisible.more }) }}
                  </p>
                </div>
                <p
                  v-else-if="batchNamePattern.trim()"
                  class="text-xs text-warning"
                >
                  {{ t('material.pieceBatchNamePatternMissingN') }}
                </p>
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
            </template>
          </ExpandableRow>

          <template v-for="group in pieceGroups" :key="group.materialTypeId">
            <li class="pt-4 pb-1 text-sm font-semibold text-base-content/80">
              {{ group.label }}
            </li>
            <ExpandableRow
              v-for="piece in group.pieces"
              :key="piece.id"
              :expanded="expandedKey === piece.id"
              @toggle="toggleRow(piece.id)"
            >
              <template #summary>
                <div class="flex flex-wrap items-baseline justify-between gap-2">
                  <span class="font-medium">{{ piece.name }}</span>
                  <span v-if="pieceSummaryMeta(piece)" class="text-sm text-base-content/70">
                    {{ pieceSummaryMeta(piece) }}
                  </span>
                </div>
              </template>
              <template #editor>
                <form class="space-y-3" @submit.prevent="updateMutation.mutate(piece.id)">
                  <select
                    v-model="editMaterialTypeId"
                    class="select select-bordered w-full"
                    required
                  >
                    <option v-for="mt in pieceTypes" :key="mt.id" :value="String(mt.id)">
                      {{ mt.name }}
                    </option>
                  </select>
                  <input
                    v-model="editPieceName"
                    type="text"
                    class="input input-bordered w-full"
                    :placeholder="t('material.pieceName')"
                    required
                  />
                  <select
                    v-if="editVariantOptions.length"
                    v-model="editVariant"
                    class="select select-bordered w-full"
                    required
                  >
                    <option disabled value="">{{ t('material.pieceVariant') }}</option>
                    <option v-for="v in editVariantOptions" :key="v" :value="v">{{ v }}</option>
                  </select>
                  <p v-if="formError && expandedKey === piece.id" class="text-sm text-error">
                    {{ formError }}
                  </p>
                  <div class="flex flex-wrap items-center justify-between gap-2">
                    <RouterLink
                      :to="`/inventories/${inventoryId}/pieces/${piece.id}`"
                      class="link link-hover text-sm"
                    >
                      {{ t('material.pieceDamagesLink') }}
                    </RouterLink>
                    <div class="flex flex-wrap gap-2">
                      <SuperuserDestructiveDelete
                        v-if="me?.isSuperuser"
                        :label="t('material.pieceDelete')"
                        :warning="t('destructive.pieceWarning')"
                        :disabled="deleteMutation.isPending.value"
                        @confirmed="deleteMutation.mutate(piece.id)"
                      />
                      <button
                        type="submit"
                        class="btn btn-primary btn-sm"
                        :disabled="updateMutation.isPending.value"
                      >
                        {{ t('material.save') }}
                      </button>
                    </div>
                  </div>
                </form>
              </template>
            </ExpandableRow>
          </template>

          <li
            v-if="!filteredPieces.length && canAddPieces && expandedKey !== NEW_ROW && expandedKey !== BATCH_ROW"
            class="py-2 text-sm opacity-70"
          >
            {{ t('material.piecesEmpty') }}
          </li>
        </ul>
      </template>
    </div>
  </div>
</template>
