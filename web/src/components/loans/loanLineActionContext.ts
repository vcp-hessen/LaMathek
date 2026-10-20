import type { LoanLine } from '../../schemas/loan'
import { gateAllows, type WorkflowStep } from '../../domain/loanWorkflowSteps'

const REVIEW_STATUSES = new Set(['draft', 'requested'])
const PACK_STATUSES = new Set(['confirmed'])
const HANDOVER_STATUSES = new Set(['packed'])
const RETURN_STATUSES = new Set(['picked_up', 'return_reported'])
const TERMINAL_STATUSES = new Set([
  'restocked',
  'unavailable',
  'withdrawn',
  'not_packed',
  'not_picked_up',
  'not_returned',
])

function isSubset(statuses: Set<string>, allowed: Set<string>): boolean {
  for (const status of statuses) {
    if (!allowed.has(status)) return false
  }
  return statuses.size > 0
}

export type LineActionHint = 'select' | 'mixed' | 'no_action' | 'wrong_step'

export type LineActionContext =
  | { kind: 'hint'; hint: LineActionHint }
  | {
      kind: 'review'
      draftCount: number
      requestedCount: number
      confirmCount: number
      declineCount: number
      withdrawCount: number
    }
  | { kind: 'pack'; count: number; declineCount: number; withdrawCount: number }
  | {
      kind: 'handover'
      pickupCount: number
      notPickedUpCount: number
      notPackedCount: number
      unpackCount: number
    }
  | {
      kind: 'return'
      pickedUpCount: number
      returnReportedCount: number
      restockCount: number
      lossCount: number
      undoPickupCount: number
    }

function stepMatchesKind(
  effectiveStep: WorkflowStep | null,
  kind: 'review' | 'pack' | 'handover' | 'return',
): boolean {
  return effectiveStep === kind
}

export function deriveLineActionContext(
  selected: LoanLine[],
  effectiveStep: WorkflowStep | null = null,
): LineActionContext {
  if (selected.length === 0) {
    return { kind: 'hint', hint: 'select' }
  }

  const statuses = new Set(selected.map((line) => line.status))

  if (isSubset(statuses, REVIEW_STATUSES)) {
    if (effectiveStep != null && !stepMatchesKind(effectiveStep, 'review')) {
      return { kind: 'hint', hint: 'wrong_step' }
    }
    const draftCount = selected.filter((l) => l.status === 'draft').length
    const requestedCount = selected.filter((l) => l.status === 'requested').length
    return {
      kind: 'review',
      draftCount,
      requestedCount,
      confirmCount: requestedCount,
      declineCount: requestedCount,
      withdrawCount: requestedCount,
    }
  }

  if (isSubset(statuses, PACK_STATUSES)) {
    if (effectiveStep != null && !stepMatchesKind(effectiveStep, 'pack')) {
      return { kind: 'hint', hint: 'wrong_step' }
    }
    return {
      kind: 'pack',
      count: selected.length,
      declineCount: selected.length,
      withdrawCount: selected.length,
    }
  }

  if (isSubset(statuses, HANDOVER_STATUSES)) {
    if (effectiveStep != null && !stepMatchesKind(effectiveStep, 'handover')) {
      return { kind: 'hint', hint: 'wrong_step' }
    }
    return {
      kind: 'handover',
      pickupCount: selected.length,
      notPickedUpCount: selected.length,
      notPackedCount: selected.length,
      unpackCount: selected.length,
    }
  }

  if (isSubset(statuses, RETURN_STATUSES)) {
    // Rückgabe melden in the return step, Übernehmen in the restock step: the
    // shared gates decide (server/lamathek/domain/workflow_gates.json).
    const pickedUpCount = selected.filter((l) => l.status === 'picked_up').length
    const returnReportedCount = selected.filter((l) => l.status === 'return_reported').length
    if (effectiveStep == null) {
      return {
        kind: 'return',
        pickedUpCount,
        returnReportedCount,
        restockCount: returnReportedCount,
        lossCount: pickedUpCount + returnReportedCount,
        undoPickupCount: pickedUpCount,
      }
    }
    const count = (action: string) =>
      selected.filter((l) => gateAllows(action, l.status, effectiveStep)).length
    const context = {
      kind: 'return' as const,
      pickedUpCount: count('report_return'),
      returnReportedCount,
      restockCount: count('restock'),
      lossCount: count('record_loss'),
      undoPickupCount: count('undo_pickup'),
    }
    if (!context.pickedUpCount && !context.restockCount && !context.lossCount && !context.undoPickupCount) {
      return { kind: 'hint', hint: 'wrong_step' }
    }
    return context
  }

  if ([...statuses].every((s) => TERMINAL_STATUSES.has(s))) {
    return { kind: 'hint', hint: 'no_action' }
  }

  return { kind: 'hint', hint: 'mixed' }
}
