<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps<{
  modelValue: string
  disabled?: boolean
  min?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  committed: [value: string]
}>()

const inputRef = ref<HTMLInputElement | null>(null)
/** Shown in the input only to anchor the native picker month when return is still empty. */
const pickerAnchorValue = ref<string | null>(null)

watch(
  () => props.modelValue,
  () => {
    pickerAnchorValue.value = null
  },
)

const displayValue = computed(() => pickerAnchorValue.value ?? props.modelValue)

function tryShowPicker() {
  const el = inputRef.value
  if (!el || el.disabled) return
  if (typeof el.showPicker === 'function') {
    try {
      el.showPicker()
      return
    } catch {
      // Not a user gesture or unsupported — fall through to focus.
    }
  }
  el.focus()
}

function onFieldClick() {
  tryShowPicker()
}

function onChange(event: Event) {
  const value = (event.target as HTMLInputElement).value
  pickerAnchorValue.value = null
  emit('update:modelValue', value)
  emit('committed', value)
}

function onBlur() {
  if (pickerAnchorValue.value && !props.modelValue.trim()) {
    pickerAnchorValue.value = null
  }
}

function focusAndShowPicker(options?: { anchorDate?: string }) {
  const el = inputRef.value
  if (!el || el.disabled) return
  const anchor = options?.anchorDate?.trim()
  if (!props.modelValue.trim() && anchor) {
    pickerAnchorValue.value = anchor
  }
  el.focus()
  nextTick(() => tryShowPicker())
}

defineExpose({ focusAndShowPicker })
</script>

<template>
  <input
    ref="inputRef"
    :value="displayValue"
    type="date"
    class="input input-bordered input-sm w-full min-w-0 tabular-nums disabled:cursor-default disabled:border-base-300/60 disabled:bg-base-200/30 disabled:opacity-90"
    :disabled="disabled"
    :min="min || undefined"
    @click="onFieldClick"
    @change="onChange"
    @blur="onBlur"
  />
</template>
