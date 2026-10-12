<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { ColumnDef } from '@tanstack/vue-table'
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
import type { Category, MaterialType, VariantAxis } from '../schemas/material'
import { variantAxesSummary } from '../utils/variantDisplay'
import { useApiErrorMessage } from '../composables/useApiErrorMessage'
import { useInventoryQueryKey } from '../composables/useInventoryQueryKey'
import DataTableFooter from './data-table/DataTableFooter.vue'
import DataTableSearch from './data-table/DataTableSearch.vue'
import { localeSortRow } from './data-table/localeSort'
import SortHeaderButton from './data-table/SortHeaderButton.vue'
import { useClientTable } from './data-table/useClientTable'
import MaterialTypeFormFields from './MaterialTypeFormFields.vue'
import SuperuserDestructiveDelete from './SuperuserDestructiveDelete.vue'
import PhotoGallery from './PhotoGallery.vue'
import PhotoThumbnail from './PhotoThumbnail.vue'

const props = defineProps<{ inventoryId: number }>()

const { t } = useI18n()
const { messageFor } = useApiErrorMessage()
const queryClient = useQueryClient()

const creating = ref(false)
const expandedId = ref<number | null>(null)
const formError = ref<string | null>(null)

const name = ref('')
const tracking = ref<'piece' | 'stock'>('piece')
const shortName = ref('')
const description = ref('')
const unit = ref('')
const consumable = ref(false)
const variants = ref<VariantAxis[]>([])
const categoryText = ref('')
const manufacturer = ref('')
const modelName = ref('')

const editName = ref('')
const editTracking = ref<'piece' | 'stock'>('piece')
const editShortName = ref('')
const editDescription = ref('')
const editUnit = ref('')
const editConsumable = ref(false)
const editVariants = ref<VariantAxis[]>([])
const editCategoryText = ref('')
const editManufacturer = ref('')
const editModelName = ref('')
const savedEdit = ref<string | null>(null)

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
    variants: VariantAxis[]
    categoryText: string
    manufacturer: string
    modelName: string
  },
): MaterialTypeWritePayload {
  const normalizedVariants = fields.variants
    .map((axis) => ({
      label: axis.label.trim(),
      values: axis.values.map((value) => value.trim()).filter(Boolean),
    }))
    .filter((axis) => axis.label && axis.values.length)
  return {
    name: fields.name,
    tracking: fields.tracking,
    shortName: fields.shortName.trim() || null,
    description: fields.description.trim() || null,
    unit: fields.tracking === 'stock' ? fields.unit.trim() || null : null,
    consumable: fields.consumable,
    variants: normalizedVariants,
    manufacturer: fields.manufacturer.trim() || null,
    modelName: fields.modelName.trim() || null,
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
  variants.value = []
  categoryText.value = ''
  manufacturer.value = ''
  modelName.value = ''
}

function materialEditSnapshot() {
  const variants = editVariants.value
    .map((axis) => ({
      label: axis.label.trim(),
      values: axis.values.map((value) => value.trim()).filter(Boolean),
    }))
    .filter((axis) => axis.label && axis.values.length)
  return JSON.stringify({
    name: editName.value,
    tracking: editTracking.value,
    shortName: editShortName.value.trim(),
    description: editDescription.value.trim(),
    unit: editTracking.value === 'stock' ? editUnit.value.trim() : '',
    consumable: editConsumable.value,
    variants,
    categoryText: editCategoryText.value.trim(),
    manufacturer: editManufacturer.value.trim(),
    modelName: editModelName.value.trim(),
  })
}

const editDirty = computed(
  () => savedEdit.value !== null && materialEditSnapshot() !== savedEdit.value,
)

function loadEditDraft(mt: MaterialType) {
  editName.value = mt.name
  editTracking.value = mt.tracking
  editShortName.value = mt.shortName ?? ''
  editDescription.value = mt.description ?? ''
  editUnit.value = mt.unit ?? ''
  editConsumable.value = mt.consumable
  editVariants.value = mt.variants.map((axis) => ({
    label: axis.label,
    values: [...axis.values],
  }))
  editCategoryText.value = mt.categoryName ?? ''
  editManufacturer.value = mt.manufacturer ?? ''
  editModelName.value = mt.modelName ?? ''
  savedEdit.value = materialEditSnapshot()
  formError.value = null
}

function openNewRow() {
  creating.value = true
  expandedId.value = null
  resetCreateDraft()
  formError.value = null
}

function closeNewRow() {
  creating.value = false
  formError.value = null
}

function toggleRow(id: number) {
  if (expandedId.value === id) {
    expandedId.value = null
    formError.value = null
    return
  }
  creating.value = false
  expandedId.value = id
  const mt = types.value?.find((row) => row.id === id)
  if (mt) loadEditDraft(mt)
}

function displayName(mt: MaterialType): string {
  return mt.shortName ? `${mt.shortName} · ${mt.name}` : mt.name
}

function trackingLabel(mt: MaterialType): string {
  return mt.tracking === 'piece' ? t('material.trackingPiece') : t('material.trackingStock')
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
        variants: variants.value,
        categoryText: categoryText.value,
        manufacturer: manufacturer.value,
        modelName: modelName.value,
      }),
    ),
  onSuccess: async () => {
    creating.value = false
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
        variants: editVariants.value,
        categoryText: editCategoryText.value,
        manufacturer: editManufacturer.value,
        modelName: editModelName.value,
      }),
    ),
  onSuccess: async () => {
    formError.value = null
    savedEdit.value = materialEditSnapshot()
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
    if (expandedId.value === id) expandedId.value = null
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

const columns = computed<ColumnDef<MaterialType>[]>(() => [
  {
    id: 'name',
    accessorFn: (mt) => displayName(mt),
    sortingFn: localeSortRow,
  },
  {
    id: 'tracking',
    accessorFn: (mt) => trackingLabel(mt),
    filterFn: (row, _columnId, value) => {
      if (!value) return true
      return row.original.tracking === value
    },
    sortingFn: localeSortRow,
  },
  {
    id: 'category',
    accessorFn: (mt) => mt.categoryName ?? '',
    filterFn: (row, _columnId, value) => {
      if (!value) return true
      return (row.original.categoryName ?? '') === value
    },
    sortingFn: localeSortRow,
  },
  {
    id: 'variants',
    accessorFn: (mt) => variantAxesSummary(mt.variants),
    sortingFn: localeSortRow,
  },
])

const categoryOptions = computed(() => {
  const names = new Set<string>()
  for (const category of categoryList.value) {
    if (category.name) names.add(category.name)
  }
  for (const mt of types.value ?? []) {
    if (mt.categoryName) names.add(mt.categoryName)
  }
  return [...names].sort((a, b) => a.localeCompare(b, 'de'))
})

const {
  table,
  globalFilter,
  sorting,
  columnFilters,
  pagination,
  tableRows,
  filteredCount,
  pageCount,
  currentPage,
  pageFrom,
  pageTo,
  goToPage,
  setPageSize,
} = useClientTable<MaterialType>({
  data: () => types.value ?? [],
  columns,
  getRowId: (mt) => String(mt.id),
  globalFilterFn: () => (row, _columnId, filterValue) => {
    const query = String(filterValue ?? '').trim().toLowerCase()
    if (!query) return true
    const mt = row.original
    const haystack = [
      displayName(mt),
      trackingLabel(mt),
      mt.categoryName ?? '',
      variantAxesSummary(mt.variants),
      mt.description ?? '',
    ]
      .join(' ')
      .toLowerCase()
    return haystack.includes(query)
  },
  initialSorting: [{ id: 'name', desc: false }],
})

const trackingFilter = computed(() => String(table.getColumn('tracking')?.getFilterValue() ?? ''))
const categoryFilter = computed(() => String(table.getColumn('category')?.getFilterValue() ?? ''))

const hasActiveFilter = computed(
  () => !!globalFilter.value.trim() || !!trackingFilter.value || !!categoryFilter.value,
)

function setTrackingFilter(value: string) {
  table.getColumn('tracking')?.setFilterValue(value || undefined)
}

function setCategoryFilter(value: string) {
  table.getColumn('category')?.setFilterValue(value || undefined)
}

function resetFilters() {
  globalFilter.value = ''
  setTrackingFilter('')
  setCategoryFilter('')
}

function sortedState(columnId: string): false | 'asc' | 'desc' {
  return table.getColumn(columnId)?.getIsSorted() ?? false
}

function onRowKeydown(event: KeyboardEvent, id: number) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    toggleRow(id)
  }
}

watch(
  [
    globalFilter,
    sorting,
    columnFilters,
    () => pagination.value.pageIndex,
    () => pagination.value.pageSize,
  ],
  () => {
    expandedId.value = null
  },
  { deep: true },
)

watch(expandedId, (id) => {
  if (id === null) return
  const mt = types.value?.find((row) => row.id === id)
  if (mt) loadEditDraft(mt)
})
</script>

<template>
  <div class="flex flex-col gap-4 text-left">
      <div class="app-section-header flex flex-wrap items-center justify-between gap-2">
        <h2 class="app-page-title">{{ t('material.typesHeading') }}</h2>
        <button
          v-if="!isLoading"
          type="button"
          class="btn btn-ghost btn-sm"
          :aria-expanded="creating"
          @click="creating ? closeNewRow() : openNewRow()"
        >
          {{ t('material.typeNew') }}
        </button>
      </div>
      <p v-if="isLoading" class="text-sm">{{ t('auth.loading') }}</p>
      <template v-else>
        <form
          v-if="creating"
          class="space-y-3 rounded-lg border border-base-200 p-4"
          @submit.prevent="createMutation.mutate()"
        >
          <p class="text-sm font-medium">{{ t('material.typeNew') }}</p>
          <MaterialTypeFormFields
            v-model:name="name"
            v-model:tracking="tracking"
            v-model:short-name="shortName"
            v-model:description="description"
            v-model:unit="unit"
            v-model:consumable="consumable"
            v-model:variants="variants"
            v-model:category-text="categoryText"
            v-model:manufacturer="manufacturer"
            v-model:model-name="modelName"
            :categories="categoryList"
          />
          <p v-if="formError && expandedId === null" class="text-sm text-error">{{ formError }}</p>
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

        <p v-if="!(types?.length)" class="text-sm opacity-70">{{ t('material.typesEmpty') }}</p>
        <div v-else class="rounded-lg border border-base-200">
          <div
            class="data-table-toolbar relative z-10 flex flex-col gap-3 border-b border-base-200 p-3 sm:flex-row sm:flex-wrap sm:items-end"
          >
            <DataTableSearch
              :model-value="globalFilter"
              :label="t('material.typesSearchLabel')"
              :placeholder="t('material.typesSearchPlaceholder')"
              @update:model-value="globalFilter = $event"
            />
            <label class="flex min-w-0 flex-col gap-1 sm:w-44">
              <span class="text-xs font-medium opacity-80">{{ t('material.filterTracking') }}</span>
              <select
                :value="trackingFilter"
                class="select select-bordered select-sm w-full"
                @change="setTrackingFilter(($event.target as HTMLSelectElement).value)"
              >
                <option value="">{{ t('material.filterAllTracking') }}</option>
                <option value="piece">{{ t('material.trackingPiece') }}</option>
                <option value="stock">{{ t('material.trackingStock') }}</option>
              </select>
            </label>
            <label class="flex min-w-0 flex-col gap-1 sm:w-48">
              <span class="text-xs font-medium opacity-80">{{ t('material.category') }}</span>
              <select
                :value="categoryFilter"
                class="select select-bordered select-sm w-full"
                @change="setCategoryFilter(($event.target as HTMLSelectElement).value)"
              >
                <option value="">{{ t('material.filterAllCategories') }}</option>
                <option v-for="categoryName in categoryOptions" :key="categoryName" :value="categoryName">
                  {{ categoryName }}
                </option>
              </select>
            </label>
            <div v-if="hasActiveFilter" class="flex sm:ms-auto">
              <button type="button" class="btn btn-ghost btn-sm" @click="resetFilters">
                {{ t('material.piecesFilterReset') }}
              </button>
            </div>
          </div>
          <div class="overflow-x-auto">
            <table class="table table-sm data-table">
              <thead>
                <tr>
                  <th class="data-table-col-photo hidden sm:table-cell">
                    <span class="sr-only">{{ t('dataTable.photo') }}</span>
                  </th>
                  <th class="data-table-col-lead">
                    <SortHeaderButton
                      :label="t('material.typesColumnName')"
                      :sorted="sortedState('name')"
                      @toggle="table.getColumn('name')?.toggleSorting()"
                    />
                  </th>
                  <th class="hidden md:table-cell">
                    <SortHeaderButton
                      :label="t('material.typesColumnTracking')"
                      :sorted="sortedState('tracking')"
                      @toggle="table.getColumn('tracking')?.toggleSorting()"
                    />
                  </th>
                  <th class="hidden lg:table-cell">
                    <SortHeaderButton
                      :label="t('material.category')"
                      :sorted="sortedState('category')"
                      @toggle="table.getColumn('category')?.toggleSorting()"
                    />
                  </th>
                  <th class="hidden xl:table-cell">
                    <SortHeaderButton
                      :label="t('material.typesColumnVariants')"
                      :sorted="sortedState('variants')"
                      @toggle="table.getColumn('variants')?.toggleSorting()"
                    />
                  </th>
                </tr>
              </thead>
              <tbody v-if="tableRows.length === 0">
                <tr>
                  <td colspan="5" class="py-8 text-center text-sm opacity-70">
                    {{ t('dataTable.noResults') }}
                  </td>
                </tr>
              </tbody>
              <tbody v-for="(row, index) in tableRows" v-else :key="row.id">
                <tr
                  tabindex="0"
                  role="button"
                  class="data-table-row cursor-pointer"
                  :class="{ 'data-table-row--stripe': index % 2 === 1 }"
                  :aria-expanded="expandedId === row.original.id"
                  @click="toggleRow(row.original.id)"
                  @keydown="onRowKeydown($event, row.original.id)"
                >
                  <td class="data-table-col-photo hidden sm:table-cell">
                    <PhotoThumbnail :photo-id="row.original.coverPhotoId" />
                  </td>
                  <td class="data-table-col-lead min-w-0">
                    <div class="flex items-start gap-2">
                      <span
                        class="mt-0.5 shrink-0 text-base-content/50 transition-transform duration-200"
                        :class="{ 'rotate-90': expandedId === row.original.id }"
                        aria-hidden="true"
                      >
                        ›
                      </span>
                      <div class="min-w-0">
                        <span class="font-medium">{{ displayName(row.original) }}</span>
                        <div class="mt-0.5 space-y-0.5 text-xs opacity-70">
                          <span class="block md:hidden">{{ trackingLabel(row.original) }}</span>
                          <span v-if="row.original.categoryName" class="block lg:hidden">
                            {{ row.original.categoryName }}
                          </span>
                          <span
                            v-if="variantAxesSummary(row.original.variants)"
                            class="block truncate xl:hidden"
                          >
                            {{ variantAxesSummary(row.original.variants) }}
                          </span>
                        </div>
                      </div>
                    </div>
                  </td>
                  <td class="hidden md:table-cell">{{ trackingLabel(row.original) }}</td>
                  <td class="hidden lg:table-cell">{{ row.original.categoryName || '—' }}</td>
                  <td class="hidden max-w-[16rem] truncate xl:table-cell">
                    {{ variantAxesSummary(row.original.variants) || '—' }}
                  </td>
                </tr>
                <tr v-if="expandedId === row.original.id" class="data-table-editor">
                  <td colspan="5" class="pb-4 pt-3">
                    <form
                      class="space-y-3 pl-5"
                      @submit.prevent="updateMutation.mutate(row.original.id)"
                    >
                      <MaterialTypeFormFields
                        v-model:name="editName"
                        v-model:tracking="editTracking"
                        v-model:short-name="editShortName"
                        v-model:description="editDescription"
                        v-model:unit="editUnit"
                        v-model:consumable="editConsumable"
                        v-model:variants="editVariants"
                        v-model:category-text="editCategoryText"
                        v-model:manufacturer="editManufacturer"
                        v-model:model-name="editModelName"
                        :categories="categoryList"
                      />
                      <div>
                        <h3 class="mb-2 text-sm font-semibold">{{ t('photos.heading') }}</h3>
                        <PhotoGallery
                          :owner="{ kind: 'materialType', materialTypeId: row.original.id }"
                          :photos="row.original.photos ?? []"
                          @change="
                            () => queryClient.invalidateQueries({ queryKey: materialTypesQueryKey })
                          "
                        />
                      </div>
                      <p v-if="formError && expandedId === row.original.id" class="text-sm text-error">
                        {{ formError }}
                      </p>
                      <div class="flex flex-wrap items-center justify-end gap-2">
                        <SuperuserDestructiveDelete
                          v-if="me?.isSuperuser"
                          :warning="t('destructive.materialTypeWarning')"
                          :disabled="deleteMutation.isPending.value"
                          @confirmed="deleteMutation.mutate(row.original.id)"
                        />
                        <button
                          type="submit"
                          class="btn btn-primary btn-sm"
                          :disabled="updateMutation.isPending.value || !editDirty"
                        >
                          {{ t('material.save') }}
                        </button>
                      </div>
                    </form>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <DataTableFooter
            :page-from="pageFrom"
            :page-to="pageTo"
            :total="filteredCount"
            :current-page="currentPage"
            :page-count="pageCount"
            :page-size="pagination.pageSize"
            @update:page-size="setPageSize"
            @go-to-page="goToPage"
          />
        </div>
      </template>
  </div>
</template>
