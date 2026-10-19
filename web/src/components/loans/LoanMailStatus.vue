<script setup lang="ts">
import { useMutation, useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { resendLoanMail } from '../../api/loans'
import { useApiErrorMessage } from '../../composables/useApiErrorMessage'
import type { OutboxMail } from '../../schemas/loan'

/** Mails of a Verleih for its Materialwart*innen: stuck ones prominently, with resend. */
const props = defineProps<{ loanId: number; mails: OutboxMail[] }>()

const { t, locale } = useI18n()
const { messageFor } = useApiErrorMessage()
const queryClient = useQueryClient()
const expanded = ref(false)
const error = ref<string | null>(null)

const stuck = computed(() =>
  props.mails.filter((m) => m.status === 'failed' || (m.status === 'pending' && m.attempts > 0)),
)
const shown = computed(() => (expanded.value ? props.mails : stuck.value))

const resend = useMutation({
  mutationFn: (mailId: number) => resendLoanMail(props.loanId, mailId),
  onSuccess: async () => {
    error.value = null
    await queryClient.invalidateQueries({ queryKey: ['loan', props.loanId] })
  },
  onError: (err) => {
    error.value = messageFor(err)
  },
})

function when(iso: string | null): string {
  return iso
    ? new Date(iso).toLocaleString(locale.value, { dateStyle: 'short', timeStyle: 'short' })
    : ''
}
</script>

<template>
  <section v-if="mails.length" class="mb-4 text-sm">
    <div
      v-if="stuck.length"
      role="status"
      class="rounded-md border border-error/40 bg-error/5 px-4 py-3"
    >
      <p class="font-medium text-error">{{ t('loans.mails.stuck', { count: stuck.length }) }}</p>
    </div>
    <ul v-if="shown.length" class="mt-2 space-y-2">
      <li
        v-for="mail in shown"
        :key="mail.id"
        class="flex flex-wrap items-center justify-between gap-2 rounded-md border border-base-300 px-3 py-2"
      >
        <div class="min-w-0">
          <p class="truncate font-medium">{{ mail.subject }}</p>
          <p class="text-xs opacity-75">
            {{ mail.audience ? t(`loans.mails.audience.${mail.audience}`) : mail.to }}
            · {{ t(`loans.mails.status.${mail.status}`) }}
            <template v-if="mail.attempts"> · {{ t('loans.mails.attempts', { count: mail.attempts }) }}</template>
            <template v-if="mail.nextAttemptAt && mail.attempts">
              · {{ t('loans.mails.nextAttempt', { time: when(mail.nextAttemptAt) }) }}
            </template>
          </p>
          <p v-if="mail.lastError && mail.status !== 'sent'" class="text-xs text-error">
            {{ mail.lastError }}
          </p>
        </div>
        <button
          v-if="mail.status === 'failed' || (mail.status === 'pending' && mail.attempts > 0)"
          type="button"
          class="btn btn-outline btn-xs"
          :disabled="resend.isPending.value"
          @click="resend.mutate(mail.id)"
        >
          {{ t('loans.mails.resend') }}
        </button>
      </li>
    </ul>
    <p v-if="error" role="alert" class="mt-1 text-xs text-error">{{ error }}</p>
    <button
      v-if="!expanded && mails.length > stuck.length"
      type="button"
      class="btn btn-ghost btn-xs mt-1"
      @click="expanded = true"
    >
      {{ t('loans.mails.showAll') }}
    </button>
  </section>
</template>
