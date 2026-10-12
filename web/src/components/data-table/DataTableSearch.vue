<script setup lang="ts">
import { MagnifyingGlassIcon } from '@heroicons/vue/24/outline'

defineProps<{
  modelValue: string
  label: string
  placeholder?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()
</script>

<template>
  <label class="flex min-w-0 flex-1 flex-col gap-1 sm:max-w-md">
    <span class="text-xs font-medium opacity-80">{{ label }}</span>
    <div class="relative">
      <MagnifyingGlassIcon
        class="pointer-events-none absolute left-2 top-1/2 size-4 -translate-y-1/2 opacity-50"
        aria-hidden="true"
      />
      <input
        :value="modelValue"
        type="search"
        class="data-table-search input input-bordered input-sm w-full min-w-0 ps-7"
        :placeholder="placeholder"
        :aria-label="label"
        autocomplete="off"
        @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      />
    </div>
  </label>
</template>
