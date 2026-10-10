<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  createMaterialType,
  deleteMaterialType,
  fetchCategories,
  fetchMaterialTypes,
  updateMaterialType,
  type MaterialTypeWritePayload,
} from '../api/material'
import { fetchMe } from '../api/me'
import type { Category, MaterialType } from '../schemas/material'
import { useApiErrorMessage } from '../composables/useApiErrorMessage'
import { useInventoryQueryKey } from '../composables/useInventoryQueryKey'
import ExpandableRow from './ExpandableRow.vue'
import MaterialTypeFormFields from './MaterialTypeFormFields.vue'
import SuperuserDestructiveDelete from './SuperuserDestructiveDelete.vue'

const NEW_ROW = 'new' as const
type ExpandedKey = number | typeof NEW_ROW | null

const props = defineProps<{ inventoryId: number }>()

const { t } = useI18n()
const { messageFor } = useApiErrorMessage()
const queryClient = useQueryClient()

const expandedKey = ref<ExpandedKey>(null)
const formError = ref<string | null>(null)

const name = ref('')
const tracking = ref<'piece' | 'stock'>('piece')
const shortName = ref('')
const description = ref('')
const unit = ref('')
const consumable = ref(false)
const variantLabel = ref('')
const variantValuesText = ref('')
const categoryText = ref('')

const editName = ref('')
const editTracking = ref<'piece' | 'stock'>('piece')
const editShortName = ref('')
const editDescription = ref('')
const editUnit = ref('')
const editConsumable = ref(false)
const editVariantLabel = ref('')
const editVariantValuesText = ref('')
const editCategoryText = ref('')

const { data: me } = useQuery({ queryKey: ['me'], queryFn: fetchMe })

const materialTypesQueryKey = useInventoryQueryKey('materialTypes', () => props.inventoryId)

const { data: types, isLoading } = useQuery({
  queryKey: materialTypesQueryKey,
  queryFn: () => fetchMaterialTypes(props.inventoryId),
})

const { data: categories } = useQuery({
  queryKey: ['categories'],
  queryFn: () => fetchCategories(),
})

const categoryList = computed(() => categories.value ?? [])

function variantValuesFromText(text: string): string[] {
  return text
    .split(/[,\n]/)
    .map((part) => part.trim())
    .filter(Boolean)
}

function categoryPart(
  text: string,
  categories: Category[],
): Pick<MaterialTypeWritePayload, 'categoryId' | 'categoryName'> {
  const trimmed = text.trim()
  if (!trimmed) return { categoryId: null }
  const match = categories.find(
    (category) => category.name.localeCompare(trimmed, 'de', { sensitivity: 'accent' }) === 0,
  )
  if (match) return { categoryId: match.id }
  return { categoryName: trimmed }
}

function buildPayload(
  fields: {
    name: string
    tracking: 'piece' | 'stock'
    shortName: string
    description: string
    unit: string
    consumable: boolean
    variantLabel: string
    variantValuesText: string
    categoryText: string
  },
): MaterialTypeWritePayload {
  return {
    name: fields.name,
    tracking: fields.tracking,
    shortName: fields.shortName.trim() || null,
    description: fields.description.trim() || null,
    unit: fields.tracking === 'stock' ? fields.unit.trim() || null : null,
    consumable: fields.consumable,
    variantLabel: fields.variantLabel.trim() || null,
    variantValues: variantValuesFromText(fields.variantValuesText),
    ...categoryPart(fields.categoryText, categoryList.value),
  }
}

function resetCreateDraft() {
  name.value = ''
  tracking.value = 'piece'
  shortName.value = ''
  description.value = ''
  unit.value = ''
  consumable.value = false
  variantLabel.value = ''
  variantValuesText.value = ''
  categoryText.value = ''
}

function loadEditDraft(mt: MaterialType) {
  editName.value = mt.name
  editTracking.value = mt.tracking
  editShortName.value = mt.shortName ?? ''
  editDescription.value = mt.description ?? ''
  editUnit.value = mt.unit ?? ''
  editConsumable.value = mt.consumable
  editVariantLabel.value = mt.variantLabel ?? ''
  editVariantValuesText.value = mt.variantValues.join(', ')
  editCategoryText.value = mt.categoryName ?? ''
  formError.value = null
}

function openNewRow() {
  expandedKey.value = NEW_ROW
  resetCreateDraft()
  formError.value = null
}

function closeNewRow() {
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
  const mt = types.value?.find((row) => row.id === id)
  if (mt) loadEditDraft(mt)
}

function trackingLabel(mt: MaterialType): string {
  return mt.tracking === 'piece' ? t('material.trackingPiece') : t('material.trackingStock')
}

function summaryMeta(mt: MaterialType): string {
  const parts: string[] = [trackingLabel(mt)]
  if (mt.categoryName) parts.push(mt.categoryName)
  if (mt.consumable) parts.push(t('material.consumableTag'))
  if (mt.tracking === 'stock' && mt.unit) parts.push(mt.unit)
  if (mt.variantValues.length) {
    parts.push(`${mt.variantLabel}: ${mt.variantValues.join(', ')}`)
  }
  return parts.join(' · ')
}

const createMutation = useMutation({
  mutationFn: () =>
    createMaterialType(
      props.inventoryId,
      buildPayload({
        name: name.value,
        tracking: tracking.value,
        shortName: shortName.value,
        description: description.value,
        unit: unit.value,
        consumable: consumable.value,
        variantLabel: variantLabel.value,
        variantValuesText: variantValuesText.value,
        categoryText: categoryText.value,
      }),
    ),
  onSuccess: async () => {
    expandedKey.value = null
    formError.value = null
    resetCreateDraft()
    await queryClient.invalidateQueries({ queryKey: ['materialTypes', props.inventoryId] })
    await queryClient.invalidateQueries({ queryKey: ['stocks', props.inventoryId] })
    await queryClient.invalidateQueries({ queryKey: ['categories'] })
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
})

const updateMutation = useMutation({
  mutationFn: (id: number) =>
    updateMaterialType(
      id,
      buildPayload({
        name: editName.value,
        tracking: editTracking.value,
        shortName: editShortName.value,
        description: editDescription.value,
        unit: editUnit.value,
        consumable: editConsumable.value,
        variantLabel: editVariantLabel.value,
        variantValuesText: editVariantValuesText.value,
        categoryText: editCategoryText.value,
      }),
    ),
  onSuccess: async () => {
    formError.value = null
    await queryClient.invalidateQueries({ queryKey: ['materialTypes', props.inventoryId] })
    await queryClient.invalidateQueries({ queryKey: ['stocks', props.inventoryId] })
    await queryClient.invalidateQueries({ queryKey: ['categories'] })
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
})

const deleteMutation = useMutation({
  mutationFn: (id: number) => deleteMaterialType(id),
  onSuccess: async (_data, id) => {
    if (expandedKey.value === id) expandedKey.value = null
    formError.value = null
    await queryClient.invalidateQueries({ queryKey: ['materialTypes', props.inventoryId] })
    await queryClient.invalidateQueries({ queryKey: ['pieces', props.inventoryId] })
    await queryClient.invalidateQueries({ queryKey: ['stocks', props.inventoryId] })
    await queryClient.invalidateQueries({ queryKey: ['sets', props.inventoryId] })
  },
  onError: (error) => {
    formError.value = messageFor(error)
  },
})

const sortedTypes = computed(() =>
  [...(types.value ?? [])].sort((a, b) => a.name.localeCompare(b.name, 'de')),
)

watch(expandedKey, (key) => {
  if (typeof key === 'number') {
    const mt = types.value?.find((row) => row.id === key)
    if (mt) loadEditDraft(mt)
  }
})
</script>

<template>
  <div class="card bg-base-100 shadow-md">
    <div class="card-body gap-4 text-left">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h2 class="card-title text-lg">{{ t('material.typesHeading') }}</h2>
        <button
          v-if="!isLoading"
          type="button"
          class="btn btn-ghost btn-sm"
          :aria-expanded="expandedKey === NEW_ROW"
          @click="openNewRow"
        >
          {{ t('material.typeNew') }}
        </button>
      </div>
      <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>
      <ul v-else class="list-none">
        <ExpandableRow
          v-if="expandedKey === NEW_ROW"
          :expanded="true"
          @toggle="closeNewRow"
        >
          <template #summary>
            <span class="font-medium">{{ t('material.typeNew') }}</span>
          </template>
          <template #editor>
            <form class="space-y-3" @submit.prevent="createMutation.mutate()">
              <MaterialTypeFormFields
                v-model:name="name"
                v-model:tracking="tracking"
                v-model:short-name="shortName"
                v-model:description="description"
                v-model:unit="unit"
                v-model:consumable="consumable"
                v-model:variant-label="variantLabel"
                v-model:variant-values-text="variantValuesText"
                v-model:category-text="categoryText"
                :categories="categoryList"
              />
              <p v-if="formError" class="text-sm text-error">{{ formError }}</p>
              <div class="flex justify-end gap-2">
                <button type="button" class="btn btn-ghost btn-sm" @click="closeNewRow">
                  {{ t('material.cancel') }}
                </button>
                <button
                  type="submit"
                  class="btn btn-primary btn-sm"
                  :disabled="createMutation.isPending.value"
                >
                  {{ t('material.typeCreate') }}
                </button>
              </div>
            </form>
          </template>
        </ExpandableRow>

        <ExpandableRow
          v-for="mt in sortedTypes"
          :key="mt.id"
          :expanded="expandedKey === mt.id"
          @toggle="toggleRow(mt.id)"
        >
          <template #summary>
            <div class="flex flex-wrap items-baseline justify-between gap-2">
              <span class="font-medium">
                <template v-if="mt.shortName">{{ mt.shortName }} · </template>{{ mt.name }}
              </span>
              <span class="text-sm text-base-content/70">{{ summaryMeta(mt) }}</span>
            </div>
          </template>
          <template #editor>
            <form class="space-y-3" @submit.prevent="updateMutation.mutate(mt.id)">
              <MaterialTypeFormFields
                v-model:name="editName"
                v-model:tracking="editTracking"
                v-model:short-name="editShortName"
                v-model:description="editDescription"
                v-model:unit="editUnit"
                v-model:consumable="editConsumable"
                v-model:variant-label="editVariantLabel"
                v-model:variant-values-text="editVariantValuesText"
                v-model:category-text="editCategoryText"
                :categories="categoryList"
              />
              <p v-if="formError && expandedKey === mt.id" class="text-sm text-error">
                {{ formError }}
              </p>
              <div class="flex flex-wrap items-center justify-end gap-2">
                <SuperuserDestructiveDelete
                  v-if="me?.isSuperuser"
                  :warning="t('destructive.materialTypeWarning')"
                  :disabled="deleteMutation.isPending.value"
                  @confirmed="deleteMutation.mutate(mt.id)"
                />
                <button
                  type="submit"
                  class="btn btn-primary btn-sm"
                  :disabled="updateMutation.isPending.value"
                >
                  {{ t('material.save') }}
                </button>
              </div>
            </form>
          </template>
        </ExpandableRow>

        <li v-if="!sortedTypes.length && expandedKey !== NEW_ROW" class="py-2 text-sm opacity-70">
          {{ t('material.typesEmpty') }}
        </li>
      </ul>
    </div>
  </div>
</template>
