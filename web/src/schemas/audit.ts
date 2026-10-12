import { z } from 'zod'

import { userSchema } from './user'

const auditUserSchema = userSchema.extend({
  sub: z.string().optional(),
})

export const auditEventSchema = z.object({
  id: z.number(),
  action: z.string(),
  reason: z.string().nullable(),
  detail: z.record(z.string(), z.unknown()).nullable().optional(),
  createdAt: z.string().nullable(),
  actor: auditUserSchema.nullable(),
  targetUser: auditUserSchema.nullable(),
})

export type AuditEvent = z.infer<typeof auditEventSchema>
