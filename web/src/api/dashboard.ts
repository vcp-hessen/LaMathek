import { api } from './client'
import { dashboardSchema, type Dashboard, type DashboardCards } from './generated/schemas'

export type { Dashboard, DashboardLoan } from './generated/schemas'

export type DashboardCard = keyof DashboardCards

/** Order of the cards on the Startseite. */
export const DASHBOARD_CARDS: readonly DashboardCard[] = [
  'conflicts',
  'stuckMails',
  'openRequests',
  'waiting',
  'returnsDue',
  'overdue',
  'openActions',
  'myLoans',
]

export async function fetchDashboard(): Promise<Dashboard> {
  const response = await api.get('/api/dashboard')
  return dashboardSchema.parse(response.data)
}
