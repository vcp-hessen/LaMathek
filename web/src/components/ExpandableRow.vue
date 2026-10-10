<script setup lang="ts">
defineProps<{
  expanded: boolean
}>()

const emit = defineEmits<{
  toggle: []
}>()
</script>

<template>
  <li class="border-b border-base-200 last:border-b-0">
    <button
      type="button"
      class="flex w-full items-start gap-2 py-3 text-left hover:bg-base-200/40 rounded-lg px-1 -mx-1"
      :aria-expanded="expanded"
      @click="emit('toggle')"
    >
      <span
        class="mt-0.5 shrink-0 text-base-content/50 transition-transform duration-200"
        :class="{ 'rotate-90': expanded }"
        aria-hidden="true"
      >
        ›
      </span>
      <div class="min-w-0 flex-1">
        <slot name="summary" />
      </div>
    </button>
    <div v-if="expanded" class="border-t border-base-200/80 pb-4 pt-3 pl-5">
      <slot name="editor" />
    </div>
  </li>
</template>
