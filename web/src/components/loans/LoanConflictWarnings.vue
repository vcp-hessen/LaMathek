<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  warnings: Array<{ code: string; otherLoanId?: number; loanId?: number }>
}>()

const { t, te } = useI18n()

const messages = computed(() =>
  props.warnings
    .map((w) => {
      const key = `loans.warnings.${w.code}`
      if (!te(key)) return w.code
      return t(key, {
        otherLoanId: w.otherLoanId ?? w.loanId ?? '',
      })
    })
    .filter(Boolean),
)
</script>

<template>
  <ul
    v-if="messages.length"
    class="mb-4 list-disc space-y-1 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950"
  >
    <li v-for="(msg, idx) in messages" :key="idx">{{ msg }}</li>
  </ul>
</template>
