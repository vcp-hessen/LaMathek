import { z } from 'zod'
import { photoMetaSchema } from './photo'

export const loanKindSchema = z.enum(['short', 'permanent'])

export const loanPhaseSchema = z.enum([
  'draft',
  'review',
  'pack',
  'handover',
  'return',
  'restock',
  'closed',
])

export const loanLineStatusSchema = z.enum([
  'draft',
  'requested',
  'confirmed',
  'packed',
  'picked_up',
  'return_reported',
  'restocked',
  'unavailable',
  'not_packed',
  'not_picked_up',
  'not_returned',
  'withdrawn',
])

const loanLineOriginSchema = z.object({
  originSetId: z.number().nullable(),
  originSetName: z.string().nullable(),
  originSetRole: z.enum(['assignment', 'optional']).nullable(),
})

/** A mail in the outbox (D0012): queued with the step, sent by the server. */
export const outboxMailSchema = z.object({
  id: z.number(),
  kind: z.string(),
  loanId: z.number().nullable(),
  audience: z.string().nullable(),
  to: z.string(),
  subject: z.string(),
  pdfKind: z.string().nullable(),
  status: z.enum(['pending', 'sending', 'sent', 'failed']),
  attempts: z.number(),
  lastError: z.string().nullable(),
  createdAt: z.string().nullable(),
  sentAt: z.string().nullable(),
  nextAttemptAt: z.string().nullable(),
})

export type OutboxMail = z.infer<typeof outboxMailSchema>

/** A conflict or hint from the availability check (D0007); also inside 409 errors. */
export const loanWarningSchema = z.object({
  code: z.string(),
  otherLoanId: z.number().optional(),
  otherLoanTitle: z.string().optional(),
  otherInventoryId: z.number().optional(),
  loanId: z.number().optional(),
  pieceId: z.number().optional(),
  lineId: z.number().optional(),
  materialTypeId: z.number().optional(),
  itemLabel: z.string().optional(),
  available: z.number().optional(),
  occupied: z.number().optional(),
  requested: z.number().optional(),
})

export type LoanWarning = z.infer<typeof loanWarningSchema>

const loanLineCommonSchema = {
  requestNotified: z.boolean().optional(),
  returnedQuantity: z.number().nullable().optional(),
  statusBeforeEnd: loanLineStatusSchema.nullable().optional(),
  warnings: z.array(loanWarningSchema).optional(),
}

export const loanLineSchema = z.discriminatedUnion('kind', [
  z.object({
    id: z.number(),
    status: loanLineStatusSchema,
    note: z.string(),
    reason: z.string(),
    replacesLineId: z.number().nullable(),
    splitFromLineId: z.number().nullable().optional(),
    kind: z.literal('piece'),
    pieceId: z.number(),
    pieceName: z.string(),
    materialTypeName: z.string(),
    ...loanLineOriginSchema.shape,
    ...loanLineCommonSchema,
  }),
  z.object({
    id: z.number(),
    status: loanLineStatusSchema,
    note: z.string(),
    reason: z.string(),
    replacesLineId: z.number().nullable(),
    splitFromLineId: z.number().nullable().optional(),
    kind: z.literal('stock'),
    materialTypeId: z.number(),
    materialTypeName: z.string(),
    /** Variant combination of the Menge (#12); empty without variants. */
    stockVariant: z.record(z.string(), z.string()).default({}),
    quantity: z.number(),
    consumable: z.boolean().optional(),
    ...loanLineOriginSchema.shape,
    ...loanLineCommonSchema,
  }),
])

export const loanSchema = z.object({
  id: z.number(),
  inventoryId: z.number(),
  inventoryName: z.string().optional(),
  kind: loanKindSchema,
  phase: loanPhaseSchema,
  // No Gruppe yet on a draft (D0003).
  groupId: z.number().nullable(),
  groupName: z.string(),
  borrowerUserId: z.number(),
  borrowerUserName: z.string(),
  borrowerPhone: z.string().optional(),
  contactUserId: z.number().nullable(),
  contactUserName: z.string().nullable(),
  contactPhone: z.string().nullable().optional(),
  eventId: z.number().nullable(),
  eventName: z.string().nullable(),
  wishPickupOn: z.string().nullable().optional(),
  wishReturnOn: z.string().nullable().optional(),
  pickupOn: z.string().nullable(),
  returnOn: z.string().nullable(),
  pickupNote: z.string(),
  returnNote: z.string(),
  coverPhotoId: z.number().nullish(),
})

export const loanDetailSchema = loanSchema.extend({
  pickupPhotos: z.array(photoMetaSchema).optional(),
  returnPhotos: z.array(photoMetaSchema).optional(),
  lines: z.array(loanLineSchema),
  warnings: z.array(loanWarningSchema).optional(),
  /** Set pieces left out when adding a Set (retired, lost, severely damaged). */
  skippedPieces: z
    .array(z.object({ pieceId: z.number(), pieceName: z.string(), code: z.string() }))
    .optional(),
  hasUnnotifiedRequestedLines: z.boolean().optional(),
  hasPendingMailChanges: z.boolean().optional(),
  /** Outbox rows of this Verleih; only sent to its Materialwart*innen. */
  mails: z.array(outboxMailSchema).optional(),
})

export const groupSchema = z.object({ id: z.number(), name: z.string() })
export const eventSchema = z.object({ id: z.number(), name: z.string() })

export type Loan = z.infer<typeof loanSchema>
export type LoanDetail = z.infer<typeof loanDetailSchema>
export type LoanLine = z.infer<typeof loanLineSchema>
