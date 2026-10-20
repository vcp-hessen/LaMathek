import { api } from './client'
import {
  calendarFeedCreatedSchema,
  calendarFeedsSchema,
  type CalendarFeed,
  type CalendarFeedCreated,
  type CalendarFeedScope,
} from './generated/schemas'

export type { CalendarFeed, CalendarFeedCreated, CalendarFeedScope }

export async function fetchCalendarFeeds(): Promise<CalendarFeed[]> {
  const response = await api.get('/api/me/calendar-feeds')
  return calendarFeedsSchema.parse(response.data).items
}

export async function createCalendarFeed(body: {
  label: string
  scope: CalendarFeedScope
  inventoryId?: number
}): Promise<CalendarFeedCreated> {
  const response = await api.post('/api/me/calendar-feeds', body)
  return calendarFeedCreatedSchema.parse(response.data)
}

export async function deleteCalendarFeed(feedId: number): Promise<void> {
  await api.delete(`/api/me/calendar-feeds/${feedId}`)
}
