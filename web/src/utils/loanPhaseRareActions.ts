import type { LoanDetail, LoanLine } from '../schemas/loan'
import {
  isLineActionAllowed,
  isWorkflowLoanPhase,
  loanWorkflowContextFromLoan,
  resolveEffectiveWorkflowStep,
} from '../domain/loanWorkflowSteps'
import {
  canCancelUnpackedLoan,
  canDeleteUnreleasedLoan,
  canSkipPickupToReturn,
} from './loanShortcutEligibility'

export type LoanPhaseRareActionId = 'delete' | 'cancel' | 'skipPickup' | 'notPickedUpAll'

export type LoanPhaseRareMenuItem = {
  id: LoanPhaseRareActionId
  labelKey: string
  confirmKey: string
  needsReason?: boolean
  lineIds?: number[]
}

export function eligibleLinesForRowAction(loan: LoanDetail, rowActionId: string): LoanLine[] {
  const ctx = loanWorkflowContextFromLoan(loan)
  const lines = loan.lines ?? []
  return lines.filter((line) => isLineActionAllowed(rowActionId, line, ctx))
}

export function buildLoanPhaseRareMenuItems(
  loan: LoanDetail,
  options: {
    isLoanBorrower: boolean
    canParticipate: boolean
    showDelete: boolean
    showCancel: boolean
    showSkipPickup: boolean
  },
): LoanPhaseRareMenuItem[] {
  const items: LoanPhaseRareMenuItem[] = []
  const ctx = loanWorkflowContextFromLoan(loan)
  const effective = resolveEffectiveWorkflowStep(ctx)

  if (options.showDelete) {
    items.push({
      id: 'delete',
      labelKey: 'loans.shortcutDelete',
      confirmKey: 'loans.shortcutDeleteConfirm',
    })
  }

  if (options.showCancel && options.canParticipate) {
    items.push({
      id: 'cancel',
      labelKey: 'loans.shortcutCancel',
      confirmKey: 'loans.shortcutCancelConfirm',
    })
  }

  if (options.showSkipPickup && options.canParticipate) {
    items.push({
      id: 'skipPickup',
      labelKey: 'loans.shortcutSkipPickup',
      confirmKey: 'loans.shortcutSkipPickupConfirm',
    })
  }

  const notPickedUpLines = eligibleLinesForRowAction(loan, 'notPickedUp')
  if (options.canParticipate && effective === 'handover' && notPickedUpLines.length > 0) {
    items.push({
      id: 'notPickedUpAll',
      labelKey: 'loans.shortcutNotPickedUpAll',
      confirmKey: 'loans.shortcutNotPickedUpAllConfirm',
      needsReason: true,
      lineIds: notPickedUpLines.map((line) => line.id),
    })
  }

  return items
}

export function canDeleteForBorrower(
  loan: LoanDetail,
  isLoanBorrower: boolean,
): boolean {
  if (!isLoanBorrower) return false
  return canDeleteUnreleasedLoan(loan.lines ?? [], loan.phase)
}

export function canDeleteLoan(
  loan: LoanDetail,
  options: { isLoanBorrower: boolean; isSuperuser: boolean },
): boolean {
  if (options.isSuperuser) return true
  return canDeleteForBorrower(loan, options.isLoanBorrower)
}

export function canCancelForLoan(loan: LoanDetail, canParticipate: boolean): boolean {
  if (!canParticipate || !isWorkflowLoanPhase(loan.phase)) return false
  return canCancelUnpackedLoan(loan.lines ?? [])
}

export function canSkipPickupForLoan(
  loan: LoanDetail,
  canParticipate: boolean,
): boolean {
  if (!canParticipate || loan.phase === 'closed') return false
  const effective = resolveEffectiveWorkflowStep(loanWorkflowContextFromLoan(loan))
  return canSkipPickupToReturn(loan.lines ?? [], effective)
}
