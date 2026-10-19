/** Verleih workflow gating — rules in server/lamathek/domain/workflow_gates.json */

import type { LoanDetail, LoanLine } from '../schemas/loan'
import workflowGates from '@shared/workflow_gates.json'

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

const HANDOVER_OR_LATER = new Set<string>(workflowGates.handoverOrLaterStatuses)

const RESTORE_TARGET_FALLBACK: Record<string, string> = workflowGates.restore.fallbackTarget

export const RESTORABLE_TERMINAL_STATUSES = new Set(Object.keys(RESTORE_TARGET_FALLBACK))

const RESTORE_VALID_TARGETS = new Set<string>(workflowGates.restore.validTargets)

const LINE_STATUS_TO_STEP = workflowGates.lineStatusToStep as Record<string, WorkflowStep>

function lineActionSteps(action: string, lineStatus: string): WorkflowStep[] | null {
  for (const rule of workflowGates.lineActions) {
    if (rule.action === action && rule.lineStatus === lineStatus) {
      return rule.steps.filter((step): step is WorkflowStep => step !== 'draft')
    }
  }
  if (action === 'remove' && lineStatus === 'draft') {
    return []
  }
  return null
}

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
  return LINE_STATUS_TO_STEP[status] ?? null
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

  const steps = lineActionSteps(action, status)
  if (!steps || steps.length === 0) {
    if (action === 'remove' && status === 'draft') return 'draft'
    return null
  }
  return steps[0]
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
  if (action === 'restore') {
    const required = actionWorkflowStep(action, line, ctx)
    if (!required || required === 'draft') return new Set()
    return new Set([required])
  }
  const steps = lineActionSteps(action, line.status)
  if (!steps) return new Set()
  return new Set(steps)
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
