import type { LoanLine } from '../schemas/loan'

const PRE_CONFIRM = new Set(['draft', 'requested'])
const CANCEL_FORBIDDEN = new Set(['packed', 'picked_up', 'return_reported'])
const SKIP_BLOCK_EARLY = new Set(['draft', 'requested', 'confirmed'])
const SKIP_BLOCK_LATE = new Set(['picked_up', 'return_reported'])

export function canDeleteUnreleasedLoan(lines: LoanLine[], phase: string): boolean {
  if (phase !== 'draft') return false
  return lines.every((line) => PRE_CONFIRM.has(line.status))
}

export function canCancelUnpackedLoan(lines: LoanLine[]): boolean {
  if (lines.some((line) => CANCEL_FORBIDDEN.has(line.status))) return false
  return lines.some((line) =>
    line.status === 'draft' || line.status === 'requested' || line.status === 'confirmed',
  )
}

export function canSkipPickupToReturn(lines: LoanLine[]): boolean {
  if (!lines.some((line) => line.status === 'packed')) return false
  if (lines.some((line) => SKIP_BLOCK_EARLY.has(line.status))) return false
  if (lines.some((line) => SKIP_BLOCK_LATE.has(line.status))) return false
  return true
}
