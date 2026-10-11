<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { VariantAxis } from '../utils/variantDisplay'

defineProps<{
  axes: VariantAxis[]
  optional?: boolean
  compact?: boolean
  /** Participate in a parent grid (up to 3 fields per row) instead of starting a new block. */
  inline?: boolean
}>()

const selection = defineModel<Record<string, string>>({ required: true })

const { t } = useI18n()
</script>

<template>
  <div
    v-if="axes.length"
    :class="
      inline
        ? 'contents'
        : 'grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3'
    "
  >
    <label v-for="axis in axes" :key="axis.label" class="flex min-w-0 flex-col gap-1">
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
