import { describe, expect, it } from 'vitest'

import workflowGates from '@shared/workflow_gates.json'
import type { LoanLine } from '../schemas/loan'
import {
  RESTORABLE_TERMINAL_STATUSES,
  isLineActionAllowed,
  restoreTargetStatus,
  workflowStepForLineStatus,
} from './loanWorkflowSteps'

function line(status: string, statusBeforeEnd: string | null = null): LoanLine {
  return {
    id: 1,
    kind: 'piece',
    pieceId: 1,
    pieceName: 'K1',
    materialTypeName: 'Kohte',
    status,
    statusBeforeEnd,
  } as unknown as LoanLine
}

describe('shared workflow gates (same JSON as the server)', () => {
  it('derives restorable statuses from the restore fallbacks', () => {
    expect([...RESTORABLE_TERMINAL_STATUSES].sort()).toEqual(
      Object.keys(workflowGates.restore.fallbackTarget).sort(),
    )
  })

  it('restores to the status before the end, else the fallback', () => {
    expect(restoreTargetStatus(line('not_returned', 'return_reported'))).toBe('return_reported')
    expect(restoreTargetStatus(line('not_returned'))).toBe('picked_up')
    expect(restoreTargetStatus(line('unavailable', 'draft'))).toBe('requested')
  })

  it('maps line statuses to workflow steps', () => {
    expect(workflowStepForLineStatus('requested')).toBe('review')
    expect(workflowStepForLineStatus('picked_up')).toBe('return')
    expect(workflowStepForLineStatus('restocked')).toBeNull()
  })

  it('allows withdrawing a confirmed line during review (D0008)', () => {
    const ctx = { phase: 'review' as const, lines: [line('requested'), line('confirmed')] }
    expect(isLineActionAllowed('withdraw', line('confirmed'), ctx)).toBe(true)
    expect(isLineActionAllowed('pack', line('confirmed'), ctx)).toBe(false)
  })
})
