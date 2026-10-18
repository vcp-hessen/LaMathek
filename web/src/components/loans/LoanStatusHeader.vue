<script setup lang="ts">
import { computed } from 'vue'
import { toRef } from 'vue'
import { useI18n } from 'vue-i18n'
import type { LoanDetail } from '../../schemas/loan'
import { useLoanWorkflowUi } from '../../composables/useLoanWorkflowUi'
import { loanDisplayName } from '../../utils/loanDisplayName'
import LoanMetaGrid from './LoanMetaGrid.vue'
import { LOAN_DETAIL_SECTION } from './loanDetailLayout'
import { borrowerStepTones, managerStepTones, stageButtonClass, stepBadgeClass } from './loanWorkflowTones'
import {
  isWorkflowLoanPhase,
  loanWorkflowContextFromLoan,
  resolveEffectiveWorkflowStep,
} from '../../domain/loanWorkflowSteps'
import ContextHelp from '../ContextHelp.vue'
import LoanPhaseCloseCluster from './LoanPhaseCloseCluster.vue'
import type { LoanPhaseRareActionId, LoanPhaseRareMenuItem } from '../../utils/loanPhaseRareActions'

const props = defineProps<{
  loan: LoanDetail
  canManage: boolean
  useManagerWorkflowSteps: boolean
  canEditBorrower: boolean
  permissionUsers: { id: number; name?: string | null; email?: string | null }[]
  isLoanBorrower: boolean
  rareMenuItems: LoanPhaseRareMenuItem[]
  shortcutPending: boolean
  completePending: boolean
  closeBlockedTitle: string
}>()

const emit = defineEmits<{
  metaSaved: []
  rareAction: [id: LoanPhaseRareActionId, payload?: { reason: string }]
  completePhase: []
}>()

const { t } = useI18n()
const loanRef = toRef(props, 'loan')
const {
  workflowHintKey,
  effectiveWorkflowStep,
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

const isManagerReviewStep = computed(
  () =>
    props.useManagerWorkflowSteps &&
    props.canManage &&
    props.loan.phase === 'review' &&
    effectiveWorkflowStep.value === 'review',
)

const workflowHintDisplayKey = computed(() => {
  if (isManagerReviewStep.value) return 'loans.workflowHint_requestedManager'
  return workflowHintKey.value
})

const statusLineKey = computed(() => {
  const { phase, kind } = props.loan
  const step = effectiveWorkflowStep.value
  if (phase === 'closed') {
    return kind === 'permanent' ? 'loans.statusLine_closedPermanent' : 'loans.statusLine_closedShort'
  }
  if (phase === 'draft') {
    return kind === 'permanent' ? 'loans.statusLine_draftPermanent' : 'loans.statusLine_draftShort'
  }
  if (isWorkflowLoanPhase(phase) && step) {
    const stepKeys: Record<string, string> = {
      review: isManagerReviewStep.value
        ? 'loans.statusLine_stepReviewManager'
        : 'loans.statusLine_stepReview',
      pack: 'loans.statusLine_stepPack',
      handover: 'loans.statusLine_stepHandover',
      return: 'loans.statusLine_stepReturn',
      restock: 'loans.statusLine_stepRestock',
    }
    const key = stepKeys[step]
    if (key) return key
  }
  return kind === 'permanent' ? 'loans.statusLine_activePermanent' : 'loans.statusLine_activeShort'
})

const displayTitle = computed(() => loanDisplayName(props.loan) || t('loans.heading'))

const phaseClose = computed(() => {
  const loan = props.loan
  const canReceipt = props.canManage || props.isLoanBorrower
  if (loan.phase === 'closed') {
    if (loan.hasPendingMailChanges && canReceipt) {
      return { labelKey: 'loans.stepReportChanges', disabled: false, remaining: 0, needsLines: false }
    }
    return null
  }
  if (loan.phase === 'draft') {
    if (!props.isLoanBorrower) return null
    const hasLines = (loan.lines?.length ?? 0) > 0
    return {
      labelKey: 'loans.phaseCloseRequest',
      disabled: !hasLines,
      remaining: 0,
      needsLines: !hasLines,
    }
  }
  const step = resolveEffectiveWorkflowStep(loanWorkflowContextFromLoan(loan))
  if (!step) return null
  const managerOnly = step === 'review' || step === 'pack' || step === 'restock'
  const allowed = managerOnly ? props.canManage : canReceipt
  if (!allowed) return null
  const openStatus: Record<string, string> = {
    review: 'requested',
    pack: 'confirmed',
    handover: 'packed',
    return: 'picked_up',
    restock: 'return_reported',
  }
  const labelKey: Record<string, string> = {
    review: 'loans.phaseCloseReview',
    pack: 'loans.phaseClosePack',
    handover: 'loans.phaseCloseHandover',
    return: 'loans.phaseCloseReturn',
    restock: 'loans.phaseCloseRestock',
  }
  const remaining = (loan.lines ?? []).filter((line) => line.status === openStatus[step]).length
  return {
    labelKey: labelKey[step] ?? 'loans.stepReportChanges',
    disabled: remaining > 0,
    remaining,
    needsLines: false,
  }
})

const phaseCloseDisabled = computed(() => {
  if (!phaseClose.value) return false
  return (
    phaseClose.value.disabled ||
    props.completePending ||
    Boolean(props.closeBlockedTitle)
  )
})

const closeHoverReason = computed(() => {
  if (!phaseCloseDisabled.value) return ''
  if (props.completePending) return t('loans.phaseClosePending')
  if (props.closeBlockedTitle) return props.closeBlockedTitle
  const offer = phaseClose.value
  if (!offer) return ''
  if (offer.needsLines) return t('loans.phaseCloseNeedsLines')
  if (offer.remaining > 0) return t('loans.phaseIncomplete', { count: offer.remaining })
  return ''
})

const closeButtonClass = computed(() => {
  if (phaseCloseDisabled.value) {
    return 'btn btn-sm border border-base-300 bg-base-200 text-base-content/45 shadow-none'
  }
  const tone = stepTones.value[stepIndex.value]
  if (!tone || tone === 'luftgrau') return 'btn btn-sm btn-primary'
  return stageButtonClass(tone, true)
})

</script>

<template>
  <section :class="LOAN_DETAIL_SECTION">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="min-w-0 flex-1 space-y-2">
        <h1 class="app-page-title">{{ displayTitle }}</h1>
        <p class="flex items-center gap-1.5 text-sm font-medium text-base-content/90">
          <span>{{ t(statusLineKey) }}</span>
          <ContextHelp anchor="verleih" :label="t('help.glossary.verleih.title')" />
        </p>
      </div>
      <LoanPhaseCloseCluster
        :phase-close-label-key="phaseClose?.labelKey ?? null"
        :close-button-class="closeButtonClass"
        :phase-close-disabled="phaseCloseDisabled"
        :close-hover-reason="closeHoverReason"
        :complete-pending="completePending"
        :rare-menu-items="rareMenuItems"
        :shortcut-pending="shortcutPending"
        @complete-phase="emit('completePhase')"
        @rare-action="(id, payload) => emit('rareAction', id, payload)"
      />
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
      <p class="text-sm text-base-content/75">{{ t(workflowHintDisplayKey) }}</p>
      <p v-if="phaseClose && phaseClose.remaining > 0" class="text-sm text-base-content/75">
        {{ t('loans.phaseIncomplete', { count: phaseClose.remaining }) }}
      </p>
      <p v-else-if="phaseClose?.needsLines" class="text-sm text-base-content/75">
        {{ t('loans.phaseCloseNeedsLines') }}
      </p>
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
