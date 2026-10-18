import type { Loan } from '../schemas/loan'

const WORKFLOW_PHASE_LABEL: Partial<Record<Loan['phase'], string>> = {
  review: 'loans.workflowStep_review',
  pack: 'loans.workflowStep_pack',
  handover: 'loans.workflowStep_handover',
  return: 'loans.workflowStep_return',
  restock: 'loans.workflowStep_restock',
}

export function loanPhaseLabelKey(phase: Loan['phase']): string {
  if (phase === 'draft') return 'loans.phaseDraft'
  if (phase === 'closed') return 'loans.phaseClosed'
  return WORKFLOW_PHASE_LABEL[phase] ?? 'loans.workflowStep_review'
}
