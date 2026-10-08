import { z } from 'zod'

export const meSchema = z.object({
  id: z.number(),
  sub: z.string().optional(),
  name: z.string().nullable().optional(),
  email: z.string().nullable().optional(),
  isSuperuser: z.boolean(),
  role: z.enum(['materialwart', 'verantwortliche']),
})

export type Me = z.infer<typeof meSchema>
