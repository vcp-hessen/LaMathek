import { z } from 'zod'

export const photoMetaSchema = z.object({
  id: z.number(),
  sortOrder: z.number(),
})

export type PhotoMeta = z.infer<typeof photoMetaSchema>
