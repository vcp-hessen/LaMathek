import { z } from 'zod'

import { api } from './client'

const dashboardLoanSchema = z.object({
  id: z.number(),
  inventoryId: z.number(),
  inventoryName: z.string(),
  title: z.string(),
  phase: z.string(),
  returnOn: z.string().nullable(),
})

export const DASHBOARD_CARDS = [
  'conflicts',
  'stuckMails',
  'openRequests',
  'waiting',
  'returnsDue',
  'overdue',
  'openActions',
  'myLoans',
] as const

export type DashboardCard = (typeof DASHBOARD_CARDS)[number]

const dashboardSchema = z.object({
  welcomeName: z.string(),
  canManage: z.boolean(),
  cards: z.record(z.string(), z.array(dashboardLoanSchema)),
})

export type DashboardLoan = z.infer<typeof dashboardLoanSchema>
export type Dashboard = z.infer<typeof dashboardSchema>

export async function fetchDashboard(): Promise<Dashboard> {
  const response = await api.get('/api/dashboard')
  return dashboardSchema.parse(response.data)
}
