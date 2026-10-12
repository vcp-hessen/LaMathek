<script setup lang="ts">
import { computed } from 'vue'
import {
  ChevronDownIcon,
  ChevronUpDownIcon,
  ChevronUpIcon,
} from '@heroicons/vue/24/outline'

const props = defineProps<{
  label: string
  sorted: false | 'asc' | 'desc'
}>()

const emit = defineEmits<{
  toggle: []
}>()

const icon = computed(() => {
  if (props.sorted === 'asc') return ChevronUpIcon
  if (props.sorted === 'desc') return ChevronDownIcon
  return ChevronUpDownIcon
})
</script>

<template>
  <button
    type="button"
    class="flex items-center gap-1 font-semibold hover:text-primary"
    @click="emit('toggle')"
  >
    {{ label }}
    <component :is="icon" class="size-4 opacity-60" aria-hidden="true" />
  </button>
</template>
