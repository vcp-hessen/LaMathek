<script setup lang="ts">
import axios from 'axios'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { useApiErrorMessage } from '../composables/useApiErrorMessage'

/** Shown instead of an empty page when loading failed (forbidden, gone, offline, …). */
const props = defineProps<{ error: unknown }>()
defineEmits<{ retry: [] }>()

const { t } = useI18n()
const { messageFor } = useApiErrorMessage()

const status = computed(() =>
  axios.isAxiosError(props.error) ? (props.error.response?.status ?? null) : null,
)

const message = computed(() => {
  if (status.value === 404) return t('app.notFound')
  if (status.value === 403) return t('app.forbidden')
  if (status.value === null) return t('app.loadFailedOffline')
  return messageFor(props.error)
})
</script>

<template>
  <div role="alert" class="rounded-md border border-error/40 bg-error/5 px-4 py-3 text-sm">
    <p>{{ message }}</p>
    <button
      v-if="status !== 403 && status !== 404"
      type="button"
      class="btn btn-ghost btn-xs mt-2"
      @click="$emit('retry')"
    >
      {{ t('app.retry') }}
    </button>
  </div>
</template>
