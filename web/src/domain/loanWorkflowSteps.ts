/** Keep in sync with server/lamathek/services/loan_workflow_steps.py */

import type { LoanDetail, LoanLine } from '../schemas/loan'

export type WorkflowStep = 'review' | 'pack' | 'handover' | 'return' | 'restock'

export type LoanWorkflowContext = {
  phase: LoanDetail['phase']
  lines: LoanLine[]
}

const WORKFLOW_PHASES = new Set<WorkflowStep>([
  'review',
  'pack',
  'handover',
  'return',
  'restock',
])

const HANDOVER_OR_LATER = new Set(['packed', 'picked_up', 'return_reported'])

export const RESTORABLE_TERMINAL_STATUSES = new Set([
  'unavailable',
  'not_packed',
  'not_picked_up',
  'not_returned',
])

const RESTORE_TARGET_FALLBACK: Record<string, string> = {
  unavailable: 'requested',
  not_packed: 'packed',
  not_picked_up: 'packed',
  not_returned: 'picked_up',
}

const RESTORE_VALID_TARGETS = new Set([
  'requested',
  'confirmed',
  'packed',
  'picked_up',
  'return_reported',
])

export function isWorkflowLoanPhase(phase: LoanDetail['phase']): phase is WorkflowStep {
  return WORKFLOW_PHASES.has(phase as WorkflowStep)
}

export function resolveEffectiveWorkflowStep(ctx: LoanWorkflowContext): WorkflowStep | null {
  if (isWorkflowLoanPhase(ctx.phase)) return ctx.phase
  return null
}

export function loanWorkflowContextFromLoan(loan: LoanDetail): LoanWorkflowContext {
  return {
    phase: loan.phase,
    lines: loan.lines ?? [],
  }
}

export function loanPastHandover(lines: LoanLine[]): boolean {
  return lines.some((line) => HANDOVER_OR_LATER.has(line.status))
}

export function workflowStepForLineStatus(status: string): WorkflowStep | null {
  if (status === 'requested') return 'review'
  if (status === 'confirmed') return 'pack'
  if (status === 'packed') return 'handover'
  if (status === 'picked_up') return 'return'
  if (status === 'return_reported') return 'restock'
  return null
}

export function restoreTargetStatus(line: LoanLine): string | null {
  const prior = line.statusBeforeEnd
  if (prior && RESTORE_VALID_TARGETS.has(prior)) return prior
  return RESTORE_TARGET_FALLBACK[line.status] ?? null
}

export function actionWorkflowStep(
  action: string,
  line: LoanLine,
  ctx: LoanWorkflowContext,
): WorkflowStep | 'draft' | null {
  const status = line.status

  if (action === 'confirm') return status === 'requested' ? 'review' : null
  if (action === 'decline' || action === 'withdraw' || action === 'replace') {
    if (status === 'requested') return 'review'
    if (status === 'confirmed') return 'pack'
    return null
  }
  if (action === 'pack') return status === 'confirmed' ? 'pack' : null
  if (action === 'unpack') return status === 'packed' ? 'pack' : null
  if (action === 'mark_not_packed' || action === 'pickup' || action === 'mark_not_picked_up') {
    return status === 'packed' ? 'handover' : null
  }
  if (action === 'undo_pickup') return status === 'picked_up' ? 'handover' : null
  if (action === 'report_return') return status === 'picked_up' ? 'return' : null
  if (action === 'restock') return status === 'return_reported' ? 'restock' : null
  if (action === 'record_loss') {
    if (status === 'picked_up') return 'return'
    if (status === 'return_reported') return 'restock'
    return null
  }
  if (action === 'restore') {
    if (RESTORABLE_TERMINAL_STATUSES.has(status)) {
      const target = restoreTargetStatus(line)
      if (!target) return null
      return workflowStepForLineStatus(target)
    }
    if (status !== 'withdrawn' || loanPastHandover(ctx.lines)) return null
    const eff = resolveEffectiveWorkflowStep(ctx)
    if (eff === 'review' || eff === 'pack') return eff
    return null
  }
  if (action === 'remove') return status === 'draft' ? 'draft' : null
  return null
}

const ROW_ACTION_TO_SERVER: Record<string, string> = {
  confirm: 'confirm',
  decline: 'decline',
  withdraw: 'withdraw',
  pack: 'pack',
  unpack: 'unpack',
  notPacked: 'mark_not_packed',
  pickup: 'pickup',
  undoPickup: 'undo_pickup',
  notPickedUp: 'mark_not_picked_up',
  reportReturn: 'report_return',
  restock: 'restock',
  recordLoss: 'record_loss',
  restore: 'restore',
  remove: 'remove',
}

export function allowedWorkflowSteps(
  rowActionId: string,
  line: LoanLine,
  ctx: LoanWorkflowContext,
): Set<WorkflowStep> {
  const action = ROW_ACTION_TO_SERVER[rowActionId]
  if (!action) return new Set()
  const required = actionWorkflowStep(action, line, ctx)
  if (!required || required === 'draft') return new Set()
  if (action === 'unpack' && line.status === 'packed') {
    return new Set(['pack', 'handover'])
  }
  return new Set([required])
}

export function isLineActionAllowed(
  rowActionId: string,
  line: LoanLine,
  ctx: LoanWorkflowContext,
): boolean {
  const action = ROW_ACTION_TO_SERVER[rowActionId]
  if (!action) return false
  if (action === 'remove') {
    return ctx.phase === 'draft' && line.status === 'draft'
  }
  const allowed = allowedWorkflowSteps(rowActionId, line, ctx)
  if (!allowed.size) return false
  if (action === 'restore' && RESTORABLE_TERMINAL_STATUSES.has(line.status)) {
    return true
  }
  const effective = resolveEffectiveWorkflowStep(ctx)
  if (!effective) return false
  return allowed.has(effective)
}

export function loanWorkflowStepIndex(step: WorkflowStep): number {
  const order: WorkflowStep[] = ['review', 'pack', 'handover', 'return', 'restock']
  return order.indexOf(step)
}
