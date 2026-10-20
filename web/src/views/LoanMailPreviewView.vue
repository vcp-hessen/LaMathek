<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { fetchLoanForKey, fetchLoanMailPreview } from '../api/loans'
import {
  defaultMailPreviewAction,
  LOAN_MAIL_PREVIEW_ACTIONS,
  type LoanMailPreviewAction,
} from '../utils/loanMailPreviewParams'
import type { LoanDetail } from '../schemas/loan'

const route = useRoute()

const loanId = computed(() => Number(route.params.loanId))
const inventoryId = computed(() => Number(route.params.id))

const action = ref<LoanMailPreviewAction>('request')
const audience = ref<'borrower' | 'managers'>('borrower')
const variant = ref('')

const VARIANT_VALUES = [
  { value: '', label: 'Standard' },
  { value: 'FromManager', label: 'FromManager' },
] as const

const AUDIENCE_TABS: { id: 'borrower' | 'managers'; label: string }[] = [
  { id: 'borrower', label: 'Ausleihende*r' },
  { id: 'managers', label: 'Materialwart*innen' },
]

function defaultVariant(loan: LoanDetail, actionId: LoanMailPreviewAction): string {
  if (actionId !== 'request' && actionId !== 'added') return ''
  if (loan.contactUserId != null && loan.contactUserId !== loan.borrowerUserId) {
    return 'FromManager'
  }
  return ''
}

const loanPhaseLabel = computed(() => {
  const loan = loanQuery.data.value
  if (!loan) return '—'
  return loan.phase
})

const loanQuery = useQuery({
  queryKey: ['loan', loanId],
  queryFn: fetchLoanForKey,
  enabled: () => Number.isFinite(loanId.value),
})

const previewInitialized = ref(false)

watch(
  loanId,
  () => {
    previewInitialized.value = false
  },
  { flush: 'sync' },
)

watch(
  () => loanQuery.data.value,
  (loan) => {
    if (!loan || previewInitialized.value) return
    action.value = defaultMailPreviewAction(loan)
    variant.value = defaultVariant(loan, action.value)
    previewInitialized.value = true
  },
  { immediate: true },
)

watch(action, (actionId) => {
  const loan = loanQuery.data.value
  if (!loan) return
  if (actionId === 'request' || actionId === 'added') {
    variant.value = defaultVariant(loan, actionId)
  } else {
    variant.value = ''
  }
})

const previewQuery = useQuery({
  queryKey: ['loan-mail-preview', loanId, action, audience, variant],
  queryFn: () =>
    fetchLoanMailPreview(loanId.value, {
      action: action.value,
      audience: audience.value,
      variant: variant.value,
    }),
  enabled: () =>
    Number.isFinite(loanId.value) &&
    loanQuery.isSuccess.value &&
    previewInitialized.value,
})

watch([action, audience, variant], () => {
  if (!previewQuery.isEnabled.value) return
  void previewQuery.refetch()
})

const previewHtml = computed(() => previewQuery.data.value?.html ?? '')
</script>

<template>
  <div class="flex min-h-0 w-full flex-1 flex-col overflow-hidden px-3 py-3 sm:px-4">
    <div class="flex shrink-0 flex-wrap items-center justify-between gap-2 pb-3">
      <div class="min-w-0">
        <h1 class="text-lg font-medium">Mail-Vorschau (Debug)</h1>
        <p class="text-xs text-base-content/60">
          mailStep aus Verleih-Phase: <span class="font-mono">{{ loanPhaseLabel }}</span>
        </p>
      </div>
      <RouterLink
        class="link link-hover shrink-0 text-sm"
        :to="`/inventories/${inventoryId}/loans/${loanId}`"
      >
        Zurück zum Verleih
      </RouterLink>
    </div>

    <div
      class="flex shrink-0 flex-wrap gap-3 rounded-lg border border-base-300 bg-base-100 p-3 text-sm"
    >
      <label class="flex min-w-[10rem] flex-1 flex-col gap-1 sm:max-w-xs">
        <span class="text-base-content/70">Mail-Aktion</span>
        <select v-model="action" class="select select-bordered select-sm w-full">
          <option v-for="id in LOAN_MAIL_PREVIEW_ACTIONS" :key="id" :value="id">
            {{ id }}
          </option>
        </select>
      </label>
      <label class="flex min-w-[8rem] flex-col gap-1 sm:max-w-[10rem]">
        <span class="text-base-content/70">Variante</span>
        <select v-model="variant" class="select select-bordered select-sm w-full">
          <option
            v-for="opt in VARIANT_VALUES"
            :key="opt.value || 'standard'"
            :value="opt.value"
          >
            {{ opt.label }}
          </option>
        </select>
      </label>
      <div class="flex min-w-[12rem] flex-col gap-1">
        <span class="text-base-content/70">Empfänger-Rolle</span>
        <div class="tabs tabs-box tabs-sm w-fit">
          <button
            v-for="tab in AUDIENCE_TABS"
            :key="tab.id"
            type="button"
            class="tab"
            :class="{ 'tab-active': audience === tab.id }"
            @click="audience = tab.id"
          >
            {{ tab.label }}
          </button>
        </div>
      </div>
    </div>

    <p
      v-if="loanQuery.isPending.value || previewQuery.isPending.value"
      class="shrink-0 py-2 text-sm opacity-70"
    >
      Lade …
    </p>
    <p v-else-if="loanQuery.isError.value" class="shrink-0 py-2 text-sm text-error">
      Verleih konnte nicht geladen werden
    </p>
    <p v-else-if="previewQuery.isError.value" class="shrink-0 py-2 text-sm text-error">
      Vorschau fehlgeschlagen
    </p>
    <p v-else class="shrink-0 truncate py-2 text-sm font-medium">
      {{ previewQuery.data.value?.subject }}
    </p>

    <div class="flex min-h-0 flex-1 justify-center overflow-hidden">
      <iframe
        v-if="previewHtml"
        class="h-full w-full max-w-[560px] rounded-lg border border-base-300 bg-base-200"
        title="Mail-Vorschau"
        sandbox=""
        :srcdoc="previewHtml"
      />
    </div>
  </div>
</template>
