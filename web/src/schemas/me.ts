import { z } from 'zod'

import { userSchema } from './user'

const impersonationStateSchema = z.object({
  actor: userSchema.extend({ sub: z.string().optional() }).nullable(),
  reason: z.string(),
  startedAt: z.string(),
})

export const meSchema = z.object({
  id: z.number(),
  sub: z.string().optional(),
  name: z.string().nullable().optional(),
  email: z.string().nullable().optional(),
  isSuperuser: z.boolean(),
  impersonation: impersonationStateSchema.nullable().optional(),
})

export type Me = z.infer<typeof meSchema>
