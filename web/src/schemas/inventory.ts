import { z } from 'zod'

export const inventorySchema = z.object({
  id: z.number(),
  name: z.string(),
})

export type Inventory = z.infer<typeof inventorySchema>

export const inventoryPermissionsSchema = z.object({
  userIds: z.array(z.number()),
})
