import { computed, type Ref } from 'vue'
import type { LoanDetail } from '../schemas/loan'
import {
  isWorkflowLoanPhase,
  resolveEffectiveWorkflowStep,
  loanWorkflowContextFromLoan,
} from '../domain/loanWorkflowSteps'

function stepToManagerIndex(step: string | null | undefined): number {
  if (step === 'review') return 0
  if (step === 'pack') return 1
  if (step === 'handover') return 2
  if (step === 'return' || step === 'restock') return 3
  return 1
}

function stepToBorrowerIndex(step: string | null | undefined, statuses: Set<string>): number {
  if (step === 'review') return 1
  if (step === 'pack' || step === 'handover') return 2
  if (step === 'return' || step === 'restock') return 3
  if (statuses.has('requested')) return 1
  if (statuses.has('picked_up') || statuses.has('return_reported')) return 3
  return 2
}

export function useLoanWorkflowUi(loan: Ref<LoanDetail | undefined>) {
  const effectiveWorkflowStep = computed(() => {
    const value = loan.value
    if (!value) return null
    return resolveEffectiveWorkflowStep(loanWorkflowContextFromLoan(value))
  })

  const workflowHintKey = computed(() => {
    const value = loan.value
    if (!value) return 'loans.workflowHint_active'
    if (value.phase === 'closed') return 'loans.workflowHint_closed'
    if (value.phase === 'draft') return 'loans.workflowHint_draft'
    const step = effectiveWorkflowStep.value
    if (step === 'review') return 'loans.workflowHint_requested'
    if (step === 'pack') return 'loans.workflowHint_confirmed'
    if (step === 'handover') return 'loans.workflowHint_packed'
    if (step === 'return') return 'loans.workflowHint_picked_up'
    if (step === 'restock') return 'loans.workflowHint_return'
    return 'loans.workflowHint_active'
  })

  const borrowerSteps = ['draft', 'request', 'pickup', 'return', 'done'] as const
  const managerSteps = ['review', 'pack', 'handover', 'return', 'done'] as const

  const borrowerStepIndex = computed(() => {
    const value = loan.value
    if (!value) return 0
    if (value.phase === 'closed') return 4
    if (value.phase === 'draft') return 0
    const statuses = new Set((value.lines ?? []).map((line) => line.status))
    return stepToBorrowerIndex(effectiveWorkflowStep.value, statuses)
  })

  const managerStepIndex = computed(() => {
    const value = loan.value
    if (!value) return 0
    if (value.phase === 'closed') return 4
    if (value.phase === 'draft') return 0
    return stepToManagerIndex(effectiveWorkflowStep.value)
  })

  return {
    workflowHintKey,
    effectiveWorkflowStep,
    borrowerSteps,
    managerSteps,
    borrowerStepIndex,
    managerStepIndex,
    isWorkflowLoanPhase,
  }
}
