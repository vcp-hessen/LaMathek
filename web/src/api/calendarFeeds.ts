import { api } from './client'

export type CalendarFeedScope = 'borrower' | 'contact' | 'inventory'

export type CalendarFeed = {
  id: number
  label: string
  scope: CalendarFeedScope
  inventoryId: number | null
  inventoryName: string
  createdAt: string | null
}

export type CalendarFeedCreated = CalendarFeed & {
  token: string
  path: string
}

export async function fetchCalendarFeeds(): Promise<CalendarFeed[]> {
  const response = await api.get('/api/me/calendar-feeds')
  return response.data.items as CalendarFeed[]
}

export async function createCalendarFeed(body: {
  label: string
  scope: CalendarFeedScope
  inventoryId?: number
}): Promise<CalendarFeedCreated> {
  const response = await api.post('/api/me/calendar-feeds', body)
  return response.data as CalendarFeedCreated
}

export async function deleteCalendarFeed(feedId: number): Promise<void> {
  await api.delete(`/api/me/calendar-feeds/${feedId}`)
}
