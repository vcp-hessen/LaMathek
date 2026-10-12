<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchMailStatus, fetchMailTestJob, startMailTest } from '../api/mail'
import { apiErrorCode } from '../api/errors'

const props = defineProps<{
  defaultRecipient: string
}>()

const { t } = useI18n()

const recipient = ref(props.defaultRecipient)
const sending = ref(false)
const feedback = ref<{ kind: 'success' | 'error'; message: string } | null>(null)

watch(
  () => props.defaultRecipient,
  (value) => {
    if (!recipient.value.trim()) {
      recipient.value = value
    }
  },
)

const { data: status, isLoading } = useQuery({
  queryKey: ['mail', 'status'],
  queryFn: fetchMailStatus,
})

let pollTimer: ReturnType<typeof setInterval> | null = null

onUnmounted(() => {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
  }
})

function stopPolling() {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function pollJob(jobId: string) {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const job = await fetchMailTestJob(jobId)
      if (job.status === 'pending') {
        return
      }
      stopPolling()
      sending.value = false
      if (job.status === 'sent') {
        feedback.value = { kind: 'success', message: t('diagnostics.mailTestSuccess') }
      } else {
        const detail = job.detail?.trim()
        feedback.value = {
          kind: 'error',
          message: detail
            ? t('diagnostics.mailTestFailedDetail', { detail })
            : t('diagnostics.mailTestFailed'),
        }
      }
    } catch {
      stopPolling()
      sending.value = false
      feedback.value = { kind: 'error', message: t('diagnostics.mailTestFailed') }
    }
  }, 800)
}

async function onSendTest() {
  feedback.value = null
  const to = recipient.value.trim()
  if (!to) {
    feedback.value = { kind: 'error', message: t('diagnostics.mailTestInvalidRecipient') }
    return
  }
  sending.value = true
  try {
    const jobId = await startMailTest(to)
    await pollJob(jobId)
  } catch (error: unknown) {
    sending.value = false
    const code = apiErrorCode(error)
    if (code === 'smtp_not_configured') {
      feedback.value = { kind: 'error', message: t('diagnostics.mailNotConfigured') }
    } else if (code === 'invalid_recipient') {
      feedback.value = { kind: 'error', message: t('diagnostics.mailTestInvalidRecipient') }
    } else {
      feedback.value = { kind: 'error', message: t('diagnostics.mailTestFailed') }
    }
  }
}

function modeLabel(mode: string): string {
  if (mode === 'ssl') return t('diagnostics.mailModeSsl')
  if (mode === 'starttls') return t('diagnostics.mailModeStarttls')
  if (mode === 'plain') return t('diagnostics.mailModePlain')
  return mode
}
</script>

<template>
  <fieldset class="space-y-3 rounded-lg border border-base-200 px-3 pb-3 pt-1">
    <legend class="px-1 text-sm font-medium">{{ t('diagnostics.mailHeading') }}</legend>
    <p v-if="isLoading" class="text-sm opacity-70">{{ t('auth.loading') }}</p>
    <template v-else-if="status">
      <p v-if="!status.configured" class="text-sm opacity-70">
        {{ t('diagnostics.mailNotConfigured') }}
      </p>
      <div
        v-else
        class="grid gap-3 text-sm sm:grid-cols-2"
      >
        <div>
          <p class="text-xs font-medium uppercase tracking-wide opacity-60">
            {{ t('diagnostics.mailStatusHost') }}
          </p>
          <p class="mt-0.5 break-all">
            {{ status.host }}:{{ status.port }}
            <span class="opacity-70">({{ modeLabel(status.mode) }})</span>
          </p>
        </div>
        <div>
          <p class="text-xs font-medium uppercase tracking-wide opacity-60">
            {{ t('diagnostics.mailStatusFrom') }}
          </p>
          <p class="mt-0.5 break-all">{{ status.fromAddress }}</p>
        </div>
      </div>

      <div v-if="status.configured" class="flex flex-col gap-2 sm:flex-row sm:items-end">
        <label class="form-control w-full sm:max-w-md">
          <span class="label-text text-sm">{{ t('diagnostics.mailTestRecipient') }}</span>
          <input
            v-model="recipient"
            type="email"
            class="input input-bordered w-full"
            :disabled="sending"
            autocomplete="email"
          />
        </label>
        <button
          type="button"
          class="btn btn-outline"
          :disabled="sending"
          @click="onSendTest"
        >
          {{ sending ? t('diagnostics.mailTestSending') : t('diagnostics.mailTestSend') }}
        </button>
      </div>

      <p
        v-if="feedback"
        class="text-sm"
        :class="feedback.kind === 'success' ? 'text-success' : 'text-error'"
      >
        {{ feedback.message }}
      </p>
    </template>
  </fieldset>
</template>
