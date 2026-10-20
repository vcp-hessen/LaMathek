import { api } from './client'
import { calendarItemsSchema, type CalendarItem } from './generated/schemas'

export { calendarItemSchema, type CalendarItem } from './generated/schemas'

/** Own Verleihe (as Ausleihende*r). */
export async function fetchBorrowerCalendar(): Promise<CalendarItem[]> {
  return calendarItemsSchema.parse((await api.get('/api/me/calendar/borrower')).data).items
}

/** Verleihe where the user is Ansprechperson. */
export async function fetchContactCalendar(): Promise<CalendarItem[]> {
  return calendarItemsSchema.parse((await api.get('/api/me/calendar/contact')).data).items
}

/** All Verleihe of an Inventar (Materialwart*innen). */
export async function fetchInventoryCalendar(inventoryId: number): Promise<CalendarItem[]> {
  return calendarItemsSchema.parse((await api.get(`/api/inventories/${inventoryId}/calendar`)).data)
    .items
}
