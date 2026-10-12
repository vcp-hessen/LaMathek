<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { XMarkIcon } from '@heroicons/vue/20/solid'
import type { MaterialType } from '../../schemas/material'
import type { VariantColumnFilterValue } from './piecesTableSetup'

const props = defineProps<{
  searchQuery: string
  materialTypeId: string
  pieceTypes: MaterialType[]
  variantFilter: VariantColumnFilterValue
}>()

const emit = defineEmits<{
  clearSearch: []
  clearMaterialType: []
  removeVariantValue: [label: string, value: string]
}>()

const { t } = useI18n()

const materialTypeName = computed(() => {
  if (!props.materialTypeId) return ''
  return props.pieceTypes.find((mt) => String(mt.id) === props.materialTypeId)?.name ?? ''
})

const variantChips = computed(() => {
  const chips: { label: string; value: string }[] = []
  for (const [label, values] of Object.entries(props.variantFilter)) {
    for (const value of values) {
      chips.push({ label, value })
    }
  }
  return chips
})

const visible = computed(
  () =>
    !!props.searchQuery.trim() ||
    !!props.materialTypeId ||
    variantChips.value.length > 0,
)
</script>

<template>
  <div
    v-if="visible"
    class="data-table-chips flex flex-wrap items-center gap-2 border-b border-base-200 px-3 py-2"
    :aria-label="t('material.piecesFilterActive')"
  >
    <span v-if="searchQuery.trim()" class="badge badge-outline gap-1 py-2.5 pl-2.5 pr-1">
      {{ t('material.piecesSearchLabel') }}: „{{ searchQuery.trim() }}“
      <button
        type="button"
        class="btn btn-ghost btn-xs btn-circle size-5 min-h-0"
        :aria-label="t('material.piecesFilterChipRemoveSearch')"
        @click="emit('clearSearch')"
      >
        <XMarkIcon class="size-3.5" />
      </button>
    </span>
    <span v-if="materialTypeName" class="badge badge-outline gap-1 py-2.5 pl-2.5 pr-1">
      {{ t('material.filterMaterialType') }}: {{ materialTypeName }}
      <button
        type="button"
        class="btn btn-ghost btn-xs btn-circle size-5 min-h-0"
        :aria-label="t('material.piecesFilterChipRemoveMaterial')"
        @click="emit('clearMaterialType')"
      >
        <XMarkIcon class="size-3.5" />
      </button>
    </span>
    <span
      v-for="chip in variantChips"
      :key="`${chip.label}-${chip.value}`"
      class="badge badge-outline gap-1 py-2.5 pl-2.5 pr-1"
    >
      {{ chip.label }}: {{ chip.value }}
      <button
        type="button"
        class="btn btn-ghost btn-xs btn-circle size-5 min-h-0"
        :aria-label="t('material.piecesFilterChipRemoveVariant', chip)"
        @click="emit('removeVariantValue', chip.label, chip.value)"
      >
        <XMarkIcon class="size-3.5" />
      </button>
    </span>
  </div>
</template>
