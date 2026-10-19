import { z } from 'zod'

const journalActorSchema = z
  .object({
    id: z.number(),
    name: z.string().nullable().optional(),
    email: z.string().nullable().optional(),
  })
  .nullable()

export const journalEntrySchema = z.object({
  id: z.number(),
  createdAt: z.string().nullable(),
  kind: z.string(),
  payload: z.record(z.unknown()),
  loanId: z.number().nullable(),
  pieceId: z.number().nullable(),
  loanLineId: z.number().nullable(),
  actor: journalActorSchema,
  /** Superuser who acted while impersonating ``actor``. */
  realActor: journalActorSchema.optional(),
})

export type JournalEntry = z.infer<typeof journalEntrySchema>
