import { z } from 'zod'
import { photoMetaSchema } from './photo'

export const loanKindSchema = z.enum(['short', 'permanent'])

export const loanStatusSchema = z.enum(['planned', 'handed_out', 'closed'])

export const returnOutcomeSchema = z.enum(['returned', 'loss'])

const loanLineReturnFieldsSchema = z.object({
  returnedQuantity: z.number(),
  lostQuantity: z.number(),
  outstandingQuantity: z.number(),
  settled: z.boolean(),
})

const loanLineOriginSchema = z.object({
  originSetId: z.number().nullable(),
  originSetName: z.string().nullable(),
  originSetRole: z.enum(['assignment', 'optional']).nullable(),
})

export const loanReturnLineSchema = z.object({
  loanLineId: z.number(),
  outcome: returnOutcomeSchema,
  quantity: z.number().nullable(),
})

export const loanReturnSchema = z.object({
  id: z.number(),
  recordedOn: z.string(),
  lines: z.array(loanReturnLineSchema),
})

export const loanSchema = z.object({
  id: z.number(),
  inventoryId: z.number(),
  kind: loanKindSchema,
  status: loanStatusSchema,
  groupId: z.number(),
  groupName: z.string(),
  responsibleUserId: z.number(),
  responsibleUserName: z.string(),
  eventId: z.number().nullable(),
  eventName: z.string().nullable(),
  startsOn: z.string().nullable(),
  endsOn: z.string().nullable(),
  coverPhotoId: z.number().nullish(),
})

export const loanLineSchema = z.discriminatedUnion('kind', [
  z.object({
    id: z.number(),
    kind: z.literal('piece'),
    pieceId: z.number(),
    pieceName: z.string(),
    materialTypeName: z.string(),
    ...loanLineOriginSchema.shape,
    ...loanLineReturnFieldsSchema.shape,
  }),
  z.object({
    id: z.number(),
    kind: z.literal('stock'),
    materialTypeId: z.number(),
    materialTypeName: z.string(),
    quantity: z.number(),
    ...loanLineOriginSchema.shape,
    ...loanLineReturnFieldsSchema.shape,
  }),
])

export const loanDetailSchema = loanSchema.extend({
  photos: z.array(photoMetaSchema).optional(),
  lines: z.array(loanLineSchema),
  returns: z.array(loanReturnSchema),
})

export const groupSchema = z.object({ id: z.number(), name: z.string() })
export const eventSchema = z.object({ id: z.number(), name: z.string() })

export type Loan = z.infer<typeof loanSchema>
export type LoanDetail = z.infer<typeof loanDetailSchema>
export type LoanLine = z.infer<typeof loanLineSchema>
