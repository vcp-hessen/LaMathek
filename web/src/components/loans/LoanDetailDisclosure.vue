<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import UiIcon from '../UiIcon.vue'

const props = withDefaults(
  defineProps<{
    open?: boolean
    title: string
    subtitle?: string | null
    titleVariant?: 'section' | 'meta'
  }>(),
  {
    titleVariant: 'section',
  },
)

const { t } = useI18n()

const titleClass = computed(() =>
  props.titleVariant === 'meta'
    ? 'text-xs font-medium uppercase tracking-wide opacity-60'
    : 'app-page-title text-base',
)
</script>

<template>
  <details
    class="group rounded-lg border border-base-300/60 bg-base-200/25 shadow-sm"
    :open="open"
  >
    <summary
      class="flex cursor-pointer list-none items-center justify-between gap-3 rounded-lg px-3 py-2.5 transition-colors hover:bg-base-200/55 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary [&::-webkit-details-marker]:hidden"
      :aria-label="`${title}. ${t('loans.disclosureToggle')}`"
    >
      <div class="min-w-0 flex-1 text-left">
        <span :class="titleClass">{{ title }}</span>
        <p
          v-if="subtitle"
          class="mt-1 text-sm font-normal leading-snug text-base-content/75 group-open:hidden"
        >
          {{ subtitle }}
        </p>
      </div>
      <UiIcon
        name="chevronDown"
        class="size-4 shrink-0 opacity-55 transition-transform group-open:rotate-180 group-hover:opacity-80"
        aria-hidden="true"
      />
    </summary>
    <div class="px-3 pb-3 pt-1">
      <slot />
    </div>
  </details>
</template>
