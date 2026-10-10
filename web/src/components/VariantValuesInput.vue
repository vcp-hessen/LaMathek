<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { VueDraggable } from 'vue-draggable-plus'

const values = defineModel<string[]>({ required: true })

const { t } = useI18n()
const draft = ref('')

function normalize(raw: string): string {
  return raw.trim()
}

function compareVariantValues(a: string, b: string): number {
  return a.localeCompare(b, 'de', { sensitivity: 'accent' })
}

function insertLexicographically(list: string[], value: string): string[] {
  const next = [...list]
  const index = next.findIndex((existing) => compareVariantValues(value, existing) < 0)
  if (index === -1) next.push(value)
  else next.splice(index, 0, value)
  return next
}

function addValues(raw: string[]) {
  let next = [...values.value]
  for (const part of raw) {
    const value = normalize(part)
    if (!value) continue
    const exists = next.some((existing) => compareVariantValues(value, existing) === 0)
    if (exists) continue
    next = insertLexicographically(next, value)
  }
  values.value = next
}

function addDraft() {
  addValues([draft.value])
  draft.value = ''
}

function removeAt(index: number) {
  values.value = values.value.filter((_, i) => i !== index)
}

function onDraftKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter') {
    event.preventDefault()
    addDraft()
  }
}

function onDraftPaste(event: ClipboardEvent) {
  const text = event.clipboardData?.getData('text') ?? ''
  if (!/[,\n]/.test(text)) return
  event.preventDefault()
  addValues(text.split(/[,\n]/))
  draft.value = ''
}
</script>

<template>
  <div class="flex min-w-0 flex-col gap-2">
    <span class="text-xs opacity-80">{{ t('material.variantValuesField') }}</span>
    <div class="join w-full min-w-0">
      <input
        v-model="draft"
        type="text"
        class="input input-bordered join-item min-w-0 flex-1"
        :placeholder="t('material.variantValuePlaceholder')"
        @keydown="onDraftKeydown"
        @paste="onDraftPaste"
      />
      <button type="button" class="btn btn-primary join-item shrink-0" @click="addDraft">
        {{ t('material.variantValueAdd') }}
      </button>
    </div>
    <VueDraggable
      v-if="values.length"
      v-model="values"
      tag="ul"
      class="variant-values-list flex w-full min-w-0 flex-wrap gap-2"
      :animation="200"
      handle=".variant-value-drag-handle"
      ghost-class="variant-value-ghost"
      chosen-class="variant-value-chosen"
      :aria-label="t('material.variantValuesField')"
    >
      <li
        v-for="(value, index) in values"
        :key="value"
        class="badge badge-outline badge-lg inline-flex h-auto max-w-full gap-1 py-2 pl-2 pr-1"
      >
        <span
          class="variant-value-drag-handle cursor-grab select-none px-0.5 text-base-content/40 active:cursor-grabbing"
          :aria-label="t('material.variantValueDrag', { value })"
          :title="t('material.variantValueDragHint')"
        >
          ⋮⋮
        </span>
        <span class="max-w-[12rem] truncate">{{ value }}</span>
        <button
          type="button"
          class="btn btn-ghost btn-xs btn-circle size-5 min-h-5 shrink-0"
          :aria-label="t('material.variantValueRemove', { value })"
          @click="removeAt(index)"
        >
          ×
        </button>
      </li>
    </VueDraggable>
    <p v-else class="text-xs opacity-60">
      {{ t('material.variantValuesEmpty') }}
    </p>
  </div>
</template>

<style scoped>
.variant-value-ghost {
  opacity: 0.35;
}

.variant-value-chosen {
  box-shadow: 0 8px 20px rgb(0 0 0 / 0.12);
}
</style>
