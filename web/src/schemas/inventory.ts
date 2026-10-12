import { z } from 'zod'
import { photoMetaSchema } from './photo'
import { userSchema } from './user'

export const inventoryVisibilitySchema = z.enum(['internal', 'active', 'archived'])

export type InventoryVisibility = z.infer<typeof inventoryVisibilitySchema>

export const inventorySchema = z.object({
  id: z.number(),
  name: z.string(),
  visibility: inventoryVisibilitySchema,
  address: z.string().nullable(),
  latitude: z.number().nullable(),
  longitude: z.number().nullable(),
  notes: z.string().nullable(),
  coverPhotoId: z.number().nullish(),
  canManage: z.boolean().optional(),
  photos: z.array(photoMetaSchema).optional(),
})

export const inventoryWriteSchema = z.object({
  name: z.string().min(1),
  visibility: inventoryVisibilitySchema.optional(),
  address: z.string().nullable().optional(),
  latitude: z.number().nullable().optional(),
  longitude: z.number().nullable().optional(),
  notes: z.string().nullable().optional(),
})

export type InventoryWritePayload = z.infer<typeof inventoryWriteSchema>

export type Inventory = z.infer<typeof inventorySchema>

export const inventoryPermissionsSchema = z.object({
  users: z.array(userSchema),
})

export const inventoryPermissionsPutSchema = z.object({
  userIds: z.array(z.number()),
  users: z.array(userSchema).optional(),
})
