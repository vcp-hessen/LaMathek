<script setup lang="ts">
import { computed } from 'vue'
import { toRef } from 'vue'
import { useI18n } from 'vue-i18n'
import type { LoanDetail } from '../../schemas/loan'
import { useLoanWorkflowUi } from '../../composables/useLoanWorkflowUi'
import { loanDisplayName } from '../../utils/loanDisplayName'
import LoanMetaGrid from './LoanMetaGrid.vue'
import { LOAN_DETAIL_SECTION } from './loanDetailLayout'
import { borrowerStepTones, managerStepTones, stepBadgeClass } from './loanWorkflowTones'

const props = defineProps<{
  loan: LoanDetail
  canManage: boolean
  useManagerWorkflowSteps: boolean
  canEditBorrower: boolean
  permissionUsers: { id: number; name?: string | null; email?: string | null }[]
  isLoanBorrower: boolean
  showDeleteShortcut: boolean
  showCancelShortcut: boolean
  showSkipPickupShortcut: boolean
  showNotifyAddedShortcut: boolean
  notifyAddedPending: boolean
  shortcutPending: boolean
}>()

const emit = defineEmits<{
  useAsBox: []
  metaSaved: []
  shortcutDelete: []
  shortcutCancel: []
  shortcutSkipPickup: []
  shortcutNotifyAdded: []
}>()

const { t } = useI18n()
const loanRef = toRef(props, 'loan')
const {
  workflowHintKey,
  borrowerSteps,
  managerSteps,
  borrowerStepIndex,
  managerStepIndex,
} = useLoanWorkflowUi(loanRef)

const steps = computed(() => (props.useManagerWorkflowSteps ? managerSteps : borrowerSteps))
const stepIndex = computed(() =>
  props.useManagerWorkflowSteps ? managerStepIndex.value : borrowerStepIndex.value,
)

const stepLabels = computed(() => {
  if (props.useManagerWorkflowSteps) {
    return [
      t('loans.workflowStep_review'),
      t('loans.workflowStep_pack'),
      t('loans.workflowStep_handover'),
      t('loans.workflowStep_return'),
      t('loans.workflowStep_done'),
    ]
  }
  return [
    t('loans.workflowStep_collect'),
    t('loans.workflowStep_request'),
    t('loans.workflowStep_pickup'),
    t('loans.workflowStep_return'),
    t('loans.workflowStep_done'),
  ]
})

const stepTones = computed(() =>
  props.useManagerWorkflowSteps ? managerStepTones : borrowerStepTones,
)

function pillState(index: number): 'current' | 'past' | 'future' {
  if (index === stepIndex.value) return 'current'
  if (index < stepIndex.value) return 'past'
  return 'future'
}

const showWorkflowTrail = computed(() => props.loan.phase !== 'closed')

const statusLineKey = computed(() => {
  const { phase, kind, openWorkflowStep } = props.loan
  if (phase === 'closed') {
    return kind === 'permanent' ? 'loans.statusLine_closedPermanent' : 'loans.statusLine_closedShort'
  }
  if (phase === 'draft') {
    return kind === 'permanent' ? 'loans.statusLine_draftPermanent' : 'loans.statusLine_draftShort'
  }
  if (phase === 'active' && openWorkflowStep) {
    const stepKeys: Record<string, string> = {
      review: 'loans.statusLine_stepReview',
      pack: 'loans.statusLine_stepPack',
      handover: 'loans.statusLine_stepHandover',
      return: 'loans.statusLine_stepReturn',
      restock: 'loans.statusLine_stepRestock',
    }
    const key = stepKeys[openWorkflowStep]
    if (key) return key
  }
  return kind === 'permanent' ? 'loans.statusLine_activePermanent' : 'loans.statusLine_activeShort'
})

const displayTitle = computed(() => loanDisplayName(props.loan) || t('loans.heading'))

</script>

<template>
  <section :class="LOAN_DETAIL_SECTION">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="min-w-0 flex-1 space-y-2">
        <h1 class="app-page-title">{{ displayTitle }}</h1>
        <p class="text-sm font-medium text-base-content/90">{{ t(statusLineKey) }}</p>
      </div>
      <button
        v-if="loan.phase === 'draft' || loan.phase === 'active'"
        type="button"
        class="btn btn-outline btn-sm shrink-0"
        @click="emit('useAsBox')"
      >
        {{ t('loans.thisLoanAsBox') }}
      </button>
    </div>

    <div v-if="showWorkflowTrail" class="space-y-2">
      <ol
        class="flex flex-wrap items-center gap-1 text-xs sm:gap-1.5"
        :aria-label="t('loans.workflowProcessHeading')"
      >
        <li
          v-for="(label, index) in stepLabels"
          :key="steps[index]"
          class="flex items-center gap-1 sm:gap-1.5"
        >
          <span
            class="badge badge-sm border whitespace-nowrap"
            :class="stepBadgeClass(stepTones[index], pillState(index))"
            :aria-current="pillState(index) === 'current' ? 'step' : undefined"
          >
            {{ label }}
          </span>
          <span
            v-if="index < stepLabels.length - 1"
            class="hidden text-base-content/25 sm:inline"
            aria-hidden="true"
          >
            →
          </span>
        </li>
      </ol>
      <p class="text-sm text-base-content/75">{{ t(workflowHintKey) }}</p>
    </div>

    <div
      v-if="
        showDeleteShortcut ||
        showCancelShortcut ||
        showSkipPickupShortcut ||
        showNotifyAddedShortcut
      "
      class="flex flex-wrap gap-x-4 gap-y-1 border-t border-base-content/10 pt-3"
    >
      <button
        v-if="showDeleteShortcut"
        type="button"
        class="link link-hover text-sm text-error no-underline hover:underline"
        :disabled="shortcutPending"
        @click="emit('shortcutDelete')"
      >
        {{ t('loans.shortcutDelete') }}
      </button>
      <button
        v-if="showCancelShortcut"
        type="button"
        class="link link-hover text-sm no-underline hover:underline"
        :disabled="shortcutPending"
        @click="emit('shortcutCancel')"
      >
        {{ t('loans.shortcutCancel') }}
      </button>
      <button
        v-if="showSkipPickupShortcut"
        type="button"
        class="link link-hover text-sm no-underline hover:underline"
        :disabled="shortcutPending"
        @click="emit('shortcutSkipPickup')"
      >
        {{ t('loans.shortcutSkipPickup') }}
      </button>
      <button
        v-if="showNotifyAddedShortcut"
        type="button"
        class="link link-hover text-sm no-underline hover:underline"
        :disabled="shortcutPending || notifyAddedPending"
        @click="emit('shortcutNotifyAdded')"
      >
        {{ t('loans.shortcutNotifyAdded') }}
      </button>
    </div>

    <LoanMetaGrid
      :loan="loan"
      :can-manage="canManage"
      :can-edit-borrower="canEditBorrower"
      :is-loan-borrower="isLoanBorrower"
      :permission-users="permissionUsers"
      @saved="emit('metaSaved')"
    />
  </section>
</template>
