<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { LoanDetail } from '../../schemas/loan'
import UiIcon from '../UiIcon.vue'
import { LOAN_DETAIL_SECTION } from './loanDetailLayout'

defineProps<{
  loan: LoanDetail
  isBorrower: boolean
  needsPhoneBeforeRequest: boolean
  phoneForRequest: string
  requestPending: boolean
  actionMessage: string | null
}>()

const emit = defineEmits<{
  'update:phoneForRequest': [value: string]
  request: []
}>()

const { t } = useI18n()
</script>

<template>
  <section
    v-if="loan.phase === 'draft' && isBorrower"
    :class="LOAN_DETAIL_SECTION"
  >
    <h2 class="app-page-title text-base">{{ t('loans.actionRequest') }}</h2>
    <p class="mb-3 text-sm opacity-70">{{ t('loans.requestHint') }}</p>
    <div
      v-if="actionMessage"
      role="alert"
      class="mb-3 flex items-start gap-2 rounded-lg border border-[#e94653]/50 bg-[#f9c5c9] px-3 py-2 text-sm leading-snug"
    >
      <UiIcon name="loss" size-class="size-5 shrink-0 text-[#e94653]" />
      <p class="min-w-0 flex-1">{{ actionMessage }}</p>
    </div>
    <form class="space-y-3" @submit.prevent="emit('request')">
      <label
        v-if="needsPhoneBeforeRequest"
        class="flex min-w-0 max-w-md flex-col gap-1"
      >
        <span class="text-xs opacity-80">{{ t('loans.phoneRequired') }}</span>
        <input
          :value="phoneForRequest"
          type="tel"
          class="input input-bordered input-sm w-full"
          required
          autocomplete="tel"
          @input="emit('update:phoneForRequest', ($event.target as HTMLInputElement).value)"
        />
        <span class="text-xs opacity-60">{{ t('loans.phoneProfileHint') }}</span>
      </label>
    </form>
  </section>
</template>
