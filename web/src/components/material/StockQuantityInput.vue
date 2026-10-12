<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  unit?: string | null
  /** Smaller height to match other detail fields */
  compact?: boolean
}>()

const quantity = defineModel<number | ''>({ required: true })

const { t } = useI18n()

const unitLabel = computed(() => {
  const trimmed = props.unit?.trim()
  return trimmed || t('material.quantityUnitFallback')
})
</script>

<template>
  <div class="join w-full max-w-[10rem]">
    <input
      v-model.number="quantity"
      type="number"
      min="0"
      step="1"
      class="input input-bordered join-item min-h-8 min-w-0 flex-1 px-2"
      :class="compact ? 'input-sm' : ''"
      required
    />
    <span
      class="join-item flex max-w-[5.5rem] shrink-0 items-center border border-base-300 bg-base-200 px-2 text-xs opacity-80"
      :title="unitLabel"
    >
      <span class="truncate">{{ unitLabel }}</span>
    </span>
  </div>
</template>
