<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import UiIcon from './UiIcon.vue'

defineProps<{
  message: string | null
  multiline?: boolean
}>()

const emit = defineEmits<{
  dismiss: []
}>()

const { t } = useI18n()
</script>

<template>
  <Teleport to="body">
    <div
      v-if="message"
      class="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex justify-center p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]"
    >
      <div
        role="alert"
        class="pointer-events-auto flex w-full max-w-lg items-start gap-2 rounded-lg border border-[#e94653]/50 bg-[#f9c5c9] px-3 py-2.5 text-sm text-base-content shadow-lg"
      >
        <UiIcon name="loss" size-class="size-5 shrink-0 text-[#e94653]" />
        <p
          class="min-w-0 flex-1 leading-snug"
          :class="multiline ? 'whitespace-pre-line' : ''"
        >
          {{ message }}
        </p>
        <button
          type="button"
          class="btn btn-ghost btn-xs btn-square shrink-0"
          :aria-label="t('feedback.dismiss')"
          @click="emit('dismiss')"
        >
          <UiIcon name="x" size-class="size-4" />
        </button>
      </div>
    </div>
  </Teleport>
</template>
