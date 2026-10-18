<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import UiIcon from './UiIcon.vue'

defineProps<{
  anchor: string
  label?: string
}>()

const { t } = useI18n()
</script>

<template>
  <RouterLink
    :to="`/hilfe#${anchor}`"
    class="inline-flex shrink-0 items-center text-base-content/50 hover:text-vcp-blau"
    :aria-label="label ?? t('help.glossaryLink')"
  >
    <UiIcon name="info" size-class="size-4" />
  </RouterLink>
</template>
