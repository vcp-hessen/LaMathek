import type { LoanLine } from '../../schemas/loan'
import {
  type LoanWorkflowContext,
  RESTORABLE_TERMINAL_STATUSES,
  isLineActionAllowed,
} from '../../domain/loanWorkflowSteps'

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
  | 'restore'
  | 'remove'

export type LineRowMenuItem = {
  id: LineRowActionId
  labelKey: string
  needsReason: boolean
  disabled?: boolean
  disabledTitleKey?: string
}

const TERMINAL_WITHOUT_ACTIONS = new Set(['restocked'])

const WORKFLOW_BLOCKED_TITLE = 'loans.actionBlockedWrongStep'

function gateItem(
  item: LineRowMenuItem,
  line: LoanLine,
  workflow: LoanWorkflowContext,
): LineRowMenuItem {
  if (item.disabled) return item
  if (!isLineActionAllowed(item.id, line, workflow)) {
    return { ...item, disabled: true, disabledTitleKey: WORKFLOW_BLOCKED_TITLE }
  }
  return item
}

export function lineRowMenuItems(
  line: LoanLine,
  options: {
    canManage: boolean
    isLoanBorrower: boolean
    canParticipate: boolean
    confirmAllowed: boolean
    workflow: LoanWorkflowContext
  },
): LineRowMenuItem[] {
  if (!options.canParticipate) return []

  const workflow = options.workflow
  const items: LineRowMenuItem[] = []
  const { status } = line

  if (status === 'draft') {
    items.push(gateItem({ id: 'remove', labelKey: 'sets.remove', needsReason: false }, line, workflow))
    return items
  }

  if (status === 'withdrawn') {
    if (options.isLoanBorrower || options.canManage) {
      items.push(
        gateItem({ id: 'restore', labelKey: 'loans.actionRestore', needsReason: false }, line, workflow),
      )
    }
    return items
  }

  if (RESTORABLE_TERMINAL_STATUSES.has(status)) {
    if (options.canManage) {
      items.push(
        gateItem(
          { id: 'restore', labelKey: 'loans.actionReopenLine', needsReason: false },
          line,
          workflow,
        ),
      )
    }
    return items
  }

  if (TERMINAL_WITHOUT_ACTIONS.has(status)) return []

  if (status === 'requested') {
    if (options.canManage) {
      items.push(
        gateItem(
          {
            id: 'confirm',
            labelKey: 'loans.actionConfirm',
            needsReason: false,
            disabled: !options.confirmAllowed,
          },
          line,
          workflow,
        ),
      )
      items.push(
        gateItem({ id: 'decline', labelKey: 'loans.actionDecline', needsReason: true }, line, workflow),
      )
    }
    if (options.isLoanBorrower || options.canManage) {
      items.push(
        gateItem({ id: 'withdraw', labelKey: 'loans.actionWithdraw', needsReason: false }, line, workflow),
      )
    }
    return items
  }

  if (status === 'confirmed') {
    if (options.canManage) {
      items.push(gateItem({ id: 'pack', labelKey: 'loans.actionPack', needsReason: false }, line, workflow))
      items.push(
        gateItem({ id: 'decline', labelKey: 'loans.actionRevokeConfirm', needsReason: true }, line, workflow),
      )
    }
    if (options.isLoanBorrower || options.canManage) {
      items.push(
        gateItem({ id: 'withdraw', labelKey: 'loans.actionWithdraw', needsReason: false }, line, workflow),
      )
    }
    return items
  }

  if (status === 'packed') {
    if (options.isLoanBorrower || options.canManage) {
      items.push(gateItem({ id: 'pickup', labelKey: 'loans.actionPickup', needsReason: false }, line, workflow))
      items.push(
        gateItem({ id: 'notPickedUp', labelKey: 'loans.actionNotPickedUp', needsReason: true }, line, workflow),
      )
    }
    if (options.canManage) {
      items.push(gateItem({ id: 'unpack', labelKey: 'loans.actionUnpack', needsReason: false }, line, workflow))
      items.push(
        gateItem({ id: 'notPacked', labelKey: 'loans.actionNotPacked', needsReason: true }, line, workflow),
      )
    }
    return items
  }

  if (status === 'picked_up') {
    if (options.isLoanBorrower || options.canManage) {
      items.push(
        gateItem({ id: 'reportReturn', labelKey: 'loans.actionReportReturn', needsReason: false }, line, workflow),
      )
      items.push(
        gateItem({ id: 'undoPickup', labelKey: 'loans.actionUndoPickup', needsReason: false }, line, workflow),
      )
    }
    if (options.canManage) {
      items.push(
        gateItem({ id: 'recordLoss', labelKey: 'loans.actionRecordLoss', needsReason: true }, line, workflow),
      )
    }
    return items
  }

  if (status === 'return_reported') {
    if (options.canManage) {
      items.push(gateItem({ id: 'restock', labelKey: 'loans.actionRestock', needsReason: false }, line, workflow))
      items.push(
        gateItem({ id: 'recordLoss', labelKey: 'loans.actionRecordLoss', needsReason: true }, line, workflow),
      )
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
    workflow: LoanWorkflowContext
  },
): { primary: LineRowMenuItem | null; alternatives: LineRowMenuItem[] } {
  const items = lineRowMenuItems(line, options)
  if (!items.length) return { primary: null, alternatives: [] }
  const primary = items[0]!
  return { primary, alternatives: items.slice(1) }
}

