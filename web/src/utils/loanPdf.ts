import type { LoanDetail } from '../schemas/loan'

export type LoanPdfKind = 'pack' | 'handover' | 'return'

type LoanPhase = LoanDetail['phase']

/** Spiegelt server/lamathek/services/loan_pdf.py (_PHASE_MIN). */
const PDF_PHASE_MIN: Record<LoanPdfKind, readonly LoanPhase[]> = {
  pack: ['pack', 'handover', 'return', 'restock', 'closed'],
  handover: ['handover', 'return', 'restock', 'closed'],
  return: ['return', 'restock', 'closed'],
}

const WORKFLOW_STEP_PDF: Partial<Record<string, LoanPdfKind>> = {
  pack: 'pack',
  handover: 'handover',
  return: 'return',
}

export function loanPdfKindsForPhase(phase: LoanPhase): LoanPdfKind[] {
  return (['pack', 'handover', 'return'] as LoanPdfKind[]).filter((kind) =>
    PDF_PHASE_MIN[kind].includes(phase),
  )
}

export function loanPdfKindForWorkflowStep(step: string): LoanPdfKind | null {
  return WORKFLOW_STEP_PDF[step] ?? null
}

export function loanPdfHref(loanId: number, kind: LoanPdfKind): string {
  return `/api/loans/${loanId}/pdf/${kind}`
}
