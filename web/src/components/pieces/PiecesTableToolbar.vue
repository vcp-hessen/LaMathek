<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { MagnifyingGlassIcon } from '@heroicons/vue/24/outline'
import type { MaterialType } from '../../schemas/material'
import type { VariantAxisCatalogEntry } from '../../utils/pieceVariantFilters'
import PiecesVariantFilter from './PiecesVariantFilter.vue'
import type { VariantColumnFilterValue } from './piecesTableSetup'

defineProps<{
  searchQuery: string
  materialTypeId: string
  pieceTypes: MaterialType[]
  variantCatalog: VariantAxisCatalogEntry[]
  variantFilter: VariantColumnFilterValue
  hasActiveFilter: boolean
}>()

const emit = defineEmits<{
  'update:searchQuery': [value: string]
  'update:materialTypeId': [value: string]
  'update:variantFilter': [value: VariantColumnFilterValue]
  reset: []
}>()

const { t } = useI18n()
</script>

<template>
  <div
    class="pieces-table-toolbar relative z-10 flex flex-col gap-3 border-b border-base-200 p-3 sm:flex-row sm:flex-wrap sm:items-end"
    :aria-label="t('material.piecesFilterActive')"
  >
    <label class="flex min-w-0 flex-1 flex-col gap-1 sm:max-w-md">
      <span class="text-xs font-medium opacity-80">{{ t('material.piecesSearchLabel') }}</span>
      <div class="relative">
        <MagnifyingGlassIcon
          class="pointer-events-none absolute left-2 top-1/2 size-4 -translate-y-1/2 opacity-50"
          aria-hidden="true"
        />
        <input
          :value="searchQuery"
          type="search"
          class="pieces-search-input input input-bordered input-sm w-full min-w-0 ps-7"
          :placeholder="t('material.piecesSearchPlaceholder')"
          :aria-label="t('material.piecesSearchLabel')"
          autocomplete="off"
          @input="emit('update:searchQuery', ($event.target as HTMLInputElement).value)"
        />
      </div>
    </label>
    <label class="flex min-w-0 flex-col gap-1 sm:w-48">
      <span class="text-xs font-medium opacity-80">{{ t('material.filterMaterialType') }}</span>
      <select
        :value="materialTypeId"
        class="select select-bordered select-sm w-full"
        @change="emit('update:materialTypeId', ($event.target as HTMLSelectElement).value)"
      >
        <option value="">{{ t('material.filterAllMaterialTypes') }}</option>
        <option v-for="mt in pieceTypes" :key="mt.id" :value="String(mt.id)">
          {{ mt.name }}
        </option>
      </select>
    </label>
    <div v-if="variantCatalog.length" class="flex flex-col gap-1">
      <span class="text-xs font-medium opacity-80">{{ t('material.piecesTableVariant') }}</span>
      <PiecesVariantFilter
        toolbar
        :catalog="variantCatalog"
        :model-value="variantFilter"
        @update:model-value="emit('update:variantFilter', $event)"
      />
    </div>
    <div v-if="hasActiveFilter" class="flex sm:ms-auto">
      <button type="button" class="btn btn-ghost btn-sm" @click="emit('reset')">
        {{ t('material.piecesFilterReset') }}
      </button>
    </div>
  </div>
</template>
