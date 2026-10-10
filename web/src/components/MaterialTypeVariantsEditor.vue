<script setup lang="ts">
import { VueDraggable } from 'vue-draggable-plus'
import { useI18n } from 'vue-i18n'
import VariantValuesInput from './VariantValuesInput.vue'
import type { VariantAxis } from '../utils/variantDisplay'

const axes = defineModel<VariantAxis[]>({ required: true })

const { t } = useI18n()

function addAxis() {
  axes.value = [...axes.value, { label: '', values: [] }]
}

function removeAxis(index: number) {
  axes.value = axes.value.filter((_, i) => i !== index)
}
</script>

<template>
  <div class="space-y-3">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <span class="text-sm font-medium">{{ t('material.variantSection') }}</span>
      <button type="button" class="btn btn-ghost btn-sm" @click="addAxis">
        {{ t('material.variantAxisAdd') }}
      </button>
    </div>
    <VueDraggable
      v-model="axes"
      tag="ul"
      class="list-none space-y-3"
      handle=".variant-axis-drag-handle"
      ghost-class="variant-axis-ghost"
    >
      <li
        v-for="(axis, index) in axes"
        :key="index"
        class="rounded-lg border border-base-200 p-3"
      >
        <div class="mb-2 flex items-start gap-2">
          <button
            type="button"
            class="variant-axis-drag-handle mt-2 cursor-grab px-0.5 text-base-content/40 active:cursor-grabbing"
            :aria-label="t('material.variantAxisDrag')"
          >
            ⋮⋮
          </button>
          <label class="flex min-w-0 flex-1 flex-col gap-1">
            <span class="text-xs opacity-80">{{ t('material.variantLabelField') }}</span>
            <input
              v-model="axis.label"
              type="text"
              class="input input-bordered input-sm w-full"
              :placeholder="t('material.variantLabelExample')"
            />
          </label>
          <button
            type="button"
            class="btn btn-ghost btn-sm mt-6"
            @click="removeAxis(index)"
          >
            {{ t('material.variantAxisRemove') }}
          </button>
        </div>
        <VariantValuesInput v-model="axis.values" />
      </li>
    </VueDraggable>
    <p v-if="!axes.length" class="text-sm opacity-70">{{ t('material.variantAxesEmpty') }}</p>
  </div>
</template>

<style scoped>
.variant-axis-ghost {
  opacity: 0.5;
}
</style>
