import { z } from 'zod'

import { api } from './client'

export const calendarItemSchema = z.object({
  loanId: z.number(),
  inventoryId: z.number(),
  inventoryName: z.string(),
  title: z.string(),
  phase: z.string(),
  pickupOn: z.string(),
  returnOn: z.string().nullable(),
  permanent: z.boolean(),
  asBorrower: z.boolean(),
  asContact: z.boolean(),
})

export type CalendarItem = z.infer<typeof calendarItemSchema>

const itemsSchema = z.object({ items: z.array(calendarItemSchema) })

/** Own Verleihe (as Ausleihende*r). */
export async function fetchBorrowerCalendar(): Promise<CalendarItem[]> {
  return itemsSchema.parse((await api.get('/api/me/calendar/borrower')).data).items
}

/** Verleihe where the user is Ansprechperson. */
export async function fetchContactCalendar(): Promise<CalendarItem[]> {
  return itemsSchema.parse((await api.get('/api/me/calendar/contact')).data).items
}

/** All Verleihe of an Inventar (Materialwart*innen). */
export async function fetchInventoryCalendar(inventoryId: number): Promise<CalendarItem[]> {
  return itemsSchema.parse((await api.get(`/api/inventories/${inventoryId}/calendar`)).data).items
}
