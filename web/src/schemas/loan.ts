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

export const loanWarningSchema = z.object({
  code: z.string(),
  otherLoanId: z.number().optional(),
  loanId: z.number().optional(),
  pieceId: z.number().optional(),
  lineId: z.number().optional(),
  materialTypeId: z.number().optional(),
})

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
  groupId: z.number(),
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
  hasUnnotifiedRequestedLines: z.boolean().optional(),
  hasPendingMailChanges: z.boolean().optional(),
})

export const groupSchema = z.object({ id: z.number(), name: z.string() })
export const eventSchema = z.object({ id: z.number(), name: z.string() })

export type Loan = z.infer<typeof loanSchema>
export type LoanDetail = z.infer<typeof loanDetailSchema>
export type LoanLine = z.infer<typeof loanLineSchema>
