<script setup lang="ts">
import { queryKeys } from '../api/queryKeys'
import { useQuery } from '@tanstack/vue-query'
import { useI18n } from 'vue-i18n'

import { fetchFailedOutbox } from '../api/mail'

/** Mails that gave up after all retries (Diagnose, superusers). */
const { t } = useI18n()
const { data: mails } = useQuery({ queryKey: queryKeys.failedMails, queryFn: fetchFailedOutbox })
</script>

<template>
  <section class="app-section gap-2">
    <h2 class="app-page-title text-base">{{ t('diagnostics.failedMailsHeading') }}</h2>
    <p v-if="!mails?.length" class="text-sm opacity-70">{{ t('diagnostics.failedMailsEmpty') }}</p>
    <ul v-else class="space-y-2 text-sm">
      <li v-for="mail in mails" :key="mail.id" class="rounded-md border border-base-300 px-3 py-2">
        <p class="font-medium">{{ mail.subject }}</p>
        <p class="text-xs opacity-75">
          {{ mail.to }} · {{ t('loans.mails.attempts', { count: mail.attempts }) }}
          <template v-if="mail.loanId"> · {{ t('diagnostics.failedMailsLoan', { id: mail.loanId }) }}</template>
        </p>
        <p v-if="mail.lastError" class="text-xs text-error">{{ mail.lastError }}</p>
      </li>
    </ul>
  </section>
</template>
