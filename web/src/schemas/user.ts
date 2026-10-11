import { z } from 'zod'

export const userSchema = z.object({
  id: z.number(),
  name: z.string().nullable(),
  email: z.string().nullable(),
  isSuperuser: z.boolean(),
})

export type User = z.infer<typeof userSchema>
