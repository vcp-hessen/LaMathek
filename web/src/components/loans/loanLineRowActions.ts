import type { LoanLine } from '../../schemas/loan'

export type LineRowActionId =
  | 'confirm'
  | 'decline'
  | 'withdraw'
  | 'pack'
  | 'unpack'
  | 'notPacked'
  | 'pickup'
  | 'undoPickup'
  | 'notPickedUp'
  | 'reportReturn'
  | 'restock'
  | 'recordLoss'
  | 'remove'

export type LineRowMenuItem = {
  id: LineRowActionId
  labelKey: string
  needsReason: boolean
  disabled?: boolean
  disabledTitleKey?: string
}

const TERMINAL = new Set([
  'restocked',
  'unavailable',
  'withdrawn',
  'not_packed',
  'not_picked_up',
  'not_returned',
])

export function lineRowMenuItems(
  line: LoanLine,
  options: {
    canManage: boolean
    isLoanBorrower: boolean
    canParticipate: boolean
    confirmAllowed: boolean
  },
): LineRowMenuItem[] {
  if (!options.canParticipate) return []

  const items: LineRowMenuItem[] = []
  const { status } = line

  if (status === 'draft') {
    items.push({ id: 'remove', labelKey: 'sets.remove', needsReason: false })
    return items
  }

  if (TERMINAL.has(status)) return []

  if (status === 'requested') {
    if (options.canManage) {
      items.push({
        id: 'confirm',
        labelKey: 'loans.actionConfirm',
        needsReason: false,
        disabled: !options.confirmAllowed,
      })
      items.push({ id: 'decline', labelKey: 'loans.actionDecline', needsReason: true })
    }
    if (options.isLoanBorrower || options.canManage) {
      items.push({ id: 'withdraw', labelKey: 'loans.actionWithdraw', needsReason: false })
    }
    return items
  }

  if (status === 'confirmed') {
    if (options.canManage) {
      items.push({ id: 'pack', labelKey: 'loans.actionPack', needsReason: false })
      items.push({ id: 'decline', labelKey: 'loans.actionRevokeConfirm', needsReason: true })
    }
    if (options.isLoanBorrower || options.canManage) {
      items.push({ id: 'withdraw', labelKey: 'loans.actionWithdraw', needsReason: false })
    }
    return items
  }

  if (status === 'packed') {
    if (options.isLoanBorrower || options.canManage) {
      items.push({ id: 'pickup', labelKey: 'loans.actionPickup', needsReason: false })
      items.push({ id: 'notPickedUp', labelKey: 'loans.actionNotPickedUp', needsReason: true })
    }
    if (options.canManage) {
      items.push({ id: 'unpack', labelKey: 'loans.actionUnpack', needsReason: false })
      items.push({ id: 'notPacked', labelKey: 'loans.actionNotPacked', needsReason: true })
    }
    return items
  }

  if (status === 'picked_up') {
    if (options.isLoanBorrower || options.canManage) {
      items.push({ id: 'reportReturn', labelKey: 'loans.actionReportReturn', needsReason: false })
      items.push({ id: 'undoPickup', labelKey: 'loans.actionUndoPickup', needsReason: false })
    }
    if (options.canManage) {
      items.push({ id: 'recordLoss', labelKey: 'loans.actionRecordLoss', needsReason: true })
    }
    return items
  }

  if (status === 'return_reported') {
    if (options.canManage) {
      items.push({ id: 'restock', labelKey: 'loans.actionRestock', needsReason: false })
      items.push({ id: 'recordLoss', labelKey: 'loans.actionRecordLoss', needsReason: true })
    }
    return items
  }

  return items
}

export function lineRowActionSplit(
  line: LoanLine,
  options: {
    canManage: boolean
    isLoanBorrower: boolean
    canParticipate: boolean
    confirmAllowed: boolean
  },
): { primary: LineRowMenuItem | null; alternatives: LineRowMenuItem[] } {
  const items = lineRowMenuItems(line, options)
  if (!items.length) return { primary: null, alternatives: [] }
  const primary = items[0]!
  return { primary, alternatives: items.slice(1) }
}

export function lineRowReasonEditable(
  line: LoanLine,
  options: {
    canManage: boolean
    isLoanBorrower: boolean
    canParticipate: boolean
    confirmAllowed: boolean
  },
): boolean {
  return lineRowMenuItems(line, options).some((item) => item.needsReason)
}
