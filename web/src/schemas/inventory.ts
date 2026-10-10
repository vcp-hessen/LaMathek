import { z } from 'zod'

export const inventorySchema = z.object({
  id: z.number(),
  name: z.string(),
  address: z.string().nullable(),
  latitude: z.number().nullable(),
  longitude: z.number().nullable(),
  notes: z.string().nullable(),
})

export const inventoryWriteSchema = z.object({
  name: z.string().min(1),
  address: z.string().nullable().optional(),
  latitude: z.number().nullable().optional(),
  longitude: z.number().nullable().optional(),
  notes: z.string().nullable().optional(),
})

export type InventoryWritePayload = z.infer<typeof inventoryWriteSchema>

export type Inventory = z.infer<typeof inventorySchema>

export const inventoryPermissionsSchema = z.object({
  userIds: z.array(z.number()),
})
