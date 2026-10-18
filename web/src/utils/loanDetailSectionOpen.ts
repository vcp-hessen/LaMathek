import type { LoanDetail } from '../schemas/loan'
import { isWorkflowLoanPhase } from '../domain/loanWorkflowSteps'

/** Default `<details open>` for loan detail sections by Verleih phase. */

export function loanMetaSectionOpen(phase: LoanDetail['phase']): boolean {
  return phase === 'draft' || phase === 'review'
}

export function loanPickupInfoSectionOpen(phase: LoanDetail['phase']): boolean {
  if (phase === 'closed') return false
  return phase === 'pack' || phase === 'handover'
}

export function loanReturnInfoSectionOpen(phase: LoanDetail['phase']): boolean {
  if (phase === 'closed') return false
  return phase === 'return' || phase === 'restock'
}

export function loanWorkflowPhase(phase: LoanDetail['phase']): string | null {
  return isWorkflowLoanPhase(phase) ? phase : null
}
