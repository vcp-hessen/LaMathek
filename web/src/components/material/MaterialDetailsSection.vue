<script setup lang="ts">
import { useI18n } from 'vue-i18n'

defineProps<{
  formError: string | null
  saving: boolean
  dirty: boolean
}>()

const emit = defineEmits<{ save: [] }>()

const { t } = useI18n()
</script>

<template>
  <section class="app-section gap-4 border-b border-base-200 pb-6 last:border-b-0">
    <h1 class="app-page-title">{{ t('material.detailsHeading') }}</h1>
    <form class="space-y-3" @submit.prevent="emit('save')">
      <slot />
      <p v-if="formError" class="text-sm text-error">{{ formError }}</p>
      <div class="flex flex-wrap items-center justify-between gap-2 pt-1">
        <slot name="delete" />
        <button
          type="submit"
          class="btn btn-primary btn-sm ms-auto"
          :disabled="saving || !dirty"
        >
          {{ t('material.save') }}
        </button>
      </div>
    </form>
  </section>
</template>
