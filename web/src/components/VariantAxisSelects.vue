<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { VariantAxis } from '../utils/variantDisplay'

defineProps<{
  axes: VariantAxis[]
  optional?: boolean
}>()

const selection = defineModel<Record<string, string>>({ required: true })

const { t } = useI18n()
</script>

<template>
  <template v-for="axis in axes" :key="axis.label">
    <label class="flex min-w-0 flex-col gap-1">
      <span class="text-xs opacity-80">{{ axis.label }}</span>
      <select
        v-model="selection[axis.label]"
        class="select select-bordered w-full"
        :required="!optional"
      >
        <option v-if="optional" value="">{{ t('material.stockLotVariantNone') }}</option>
        <option v-for="value in axis.values" :key="value" :value="value">{{ value }}</option>
      </select>
    </label>
  </template>
</template>
