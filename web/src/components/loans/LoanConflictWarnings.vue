<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import type { LoanWarning } from '../../schemas/loan'

/** Conflicts from the availability check (D0007), each naming its item and the other Verleih. */
defineProps<{
  warnings: LoanWarning[]
  /** Hide the item label (e.g. on a piece page, where the item is obvious). */
  hideItem?: boolean
}>()

const { t, te } = useI18n()

function keyFor(warning: LoanWarning): string | null {
  const key = `loans.warnings.${warning.code}`
  return te(key) ? key : null
}

function stockValues(warning: LoanWarning) {
  const available = warning.available ?? 0
  return {
    available,
    free: Math.max(0, available - (warning.occupied ?? 0)),
    requested: warning.requested ?? 0,
  }
}

function otherLoanRoute(warning: LoanWarning) {
  if (warning.otherLoanId == null || warning.otherInventoryId == null) return null
  return {
    name: 'loan-detail',
    params: { id: warning.otherInventoryId, loanId: warning.otherLoanId },
  }
}
</script>

<template>
  <div
    v-if="warnings.length"
    role="status"
    class="mb-4 rounded-md border border-warning/50 bg-warning/10 px-4 py-3 text-sm"
  >
    <p class="mb-1 font-medium">{{ t('loans.warnings.heading') }}</p>
    <ul class="list-disc space-y-1 pl-4">
      <li v-for="(warning, idx) in warnings" :key="idx">
        <template v-if="!hideItem && warning.itemLabel">
          <span class="font-medium">{{ warning.itemLabel }}</span>:
        </template>
        <i18n-t v-if="keyFor(warning)" :keypath="keyFor(warning)!" tag="span" scope="global">
          <template #other>
            <RouterLink
              v-if="otherLoanRoute(warning)"
              :to="otherLoanRoute(warning)!"
              class="link link-hover font-medium"
            >
              „{{ warning.otherLoanTitle || `#${warning.otherLoanId}` }}“
            </RouterLink>
            <span v-else>{{ t('loans.warnings.unknownLoan') }}</span>
          </template>
          <template #free>{{ stockValues(warning).free }}</template>
          <template #available>{{ stockValues(warning).available }}</template>
          <template #requested>{{ stockValues(warning).requested }}</template>
        </i18n-t>
        <span v-else>{{ warning.code }}</span>
      </li>
    </ul>
  </div>
</template>
