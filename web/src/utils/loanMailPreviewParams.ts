import type { LoanDetail } from '../schemas/loan'

/** Server mail actions exposed in the debug preview. */
export const LOAN_MAIL_PREVIEW_ACTIONS = [
  'request',
  'added',
  'confirm',
  'pack',
  'pickup',
  'report_return',
  'restock',
  'changes',
] as const

export type LoanMailPreviewAction = (typeof LOAN_MAIL_PREVIEW_ACTIONS)[number]

const PHASE_TO_DEFAULT_ACTION: Partial<Record<LoanDetail['phase'], LoanMailPreviewAction>> = {
  draft: 'request',
  review: 'request',
  pack: 'pack',
  handover: 'pickup',
  return: 'report_return',
  restock: 'restock',
  closed: 'restock',
}

export function defaultMailPreviewAction(loan: LoanDetail): LoanMailPreviewAction {
  return PHASE_TO_DEFAULT_ACTION[loan.phase] ?? 'request'
}
