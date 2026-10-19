import { z } from 'zod'

export const userSchema = z.object({
  id: z.number(),
  name: z.string().nullable(),
  email: z.string().nullable(),
  phone: z.string().optional(),
  isSuperuser: z.boolean(),
  hasLogin: z.boolean().optional(),
})

export type User = z.infer<typeof userSchema>

export const managedUserSchema = userSchema.extend({
  inventoryIds: z.array(z.number()),
  /** Phone and email are only sent and editable where the viewer may change them. */
  canEditContact: z.boolean().optional(),
})

export type ManagedUser = z.infer<typeof managedUserSchema>
