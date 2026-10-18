import type { Composer } from 'vue-i18n'
import type { WlzTriState } from './wlzTriState'

export type InventoryCalendarScope = 'off' | 'contact' | 'all'

export type BorrowerCalendarScope = 'off' | 'borrower'

export type CalendarScopeSwitchValue = InventoryCalendarScope | BorrowerCalendarScope

export function inventoryScopeToTriState(scope: InventoryCalendarScope): WlzTriState {
  switch (scope) {
    case 'contact':
      return 'partial'
    case 'all':
      return 'on'
    default:
      return 'off'
  }
}

export function triStateToInventoryScope(state: WlzTriState): InventoryCalendarScope {
  switch (state) {
    case 'partial':
      return 'contact'
    case 'on':
      return 'all'
    default:
      return 'off'
  }
}

export function borrowerScopeToTriState(scope: BorrowerCalendarScope): WlzTriState {
  return scope === 'borrower' ? 'on' : 'off'
}

export function triStateToBorrowerScope(state: WlzTriState): BorrowerCalendarScope {
  return state === 'on' ? 'borrower' : 'off'
}

export function cycleInventoryScope(
  scope: InventoryCalendarScope,
  canManage: boolean,
): InventoryCalendarScope {
  if (scope === 'off') return 'contact'
  if (scope === 'contact') return canManage ? 'all' : 'off'
  return 'off'
}

export function cycleBorrowerScope(scope: BorrowerCalendarScope): BorrowerCalendarScope {
  return scope === 'borrower' ? 'off' : 'borrower'
}

export function calendarInventoryLabel(
  t: Composer['t'],
  inventoryName: string,
  scope: 'contact' | 'all',
): string {
  const scopeLabel =
    scope === 'contact' ? t('calendar.contentContact') : t('calendar.contentAllLoans')
  return t('calendar.contentInventoryLine', { name: inventoryName, scope: scopeLabel })
}
