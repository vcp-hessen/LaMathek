<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { VariantAxis } from '../utils/variantDisplay'

const props = withDefaults(
  defineProps<{
    axes: VariantAxis[]
    optional?: boolean
    compact?: boolean
    /** Participate in a parent grid instead of starting a new block. */
    inline?: boolean
    /** Column count from the `lg` breakpoint upward (standalone grid only). */
    columns?: 3 | 4
  }>(),
  { columns: 4 },
)

const selection = defineModel<Record<string, string>>({ required: true })

const { t } = useI18n()

const gridClass = computed(() => {
  if (props.inline) return 'contents'
  const lgCols = props.columns === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-4'
  return `grid grid-cols-1 gap-3 sm:grid-cols-2 ${lgCols}`
})
</script>

<template>
  <div v-if="axes.length" :class="gridClass">
    <label v-for="axis in axes" :key="axis.label" class="flex min-w-0 flex-col gap-0.5">
      <span class="text-xs opacity-80">{{ axis.label }}</span>
      <select
        v-model="selection[axis.label]"
        class="select select-bordered w-full min-w-0"
        :class="{ 'select-sm': compact }"
        :required="!optional"
      >
        <option v-if="optional" value="">{{ t('material.stockLotVariantNone') }}</option>
        <option v-for="value in axis.values" :key="value" :value="value">{{ value }}</option>
      </select>
    </label>
  </div>
</template>
