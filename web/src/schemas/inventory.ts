import { z } from 'zod'

import { inventoryVisibilitySchema } from '../api/generated/schemas'

export {
  inventoryDetailSchema,
  inventoryPermissionsSchema,
  inventorySchema,
  inventoryVisibilitySchema,
  type Inventory,
  type InventoryDetail,
  type InventoryPermissions,
  type InventoryVisibility,
} from '../api/generated/schemas'

/** Request body of POST/PATCH; requests are not part of the generated contract yet. */
export const inventoryWriteSchema = z.object({
  name: z.string().min(1),
  visibility: inventoryVisibilitySchema.optional(),
  address: z.string().nullable().optional(),
  latitude: z.number().nullable().optional(),
  longitude: z.number().nullable().optional(),
  notes: z.string().nullable().optional(),
})

export type InventoryWritePayload = z.infer<typeof inventoryWriteSchema>
