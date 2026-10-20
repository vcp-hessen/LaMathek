import { z } from 'zod'
import { pieceSchema } from './material'
import { photoMetaSchema } from './photo'

export const setSummarySchema = z.object({
  id: z.number(),
  inventoryId: z.number(),
  name: z.string(),
  shortName: z.string().nullable(),
  coverPhotoId: z.number().nullish(),
  assignmentPieceIds: z.array(z.number()),
  optionalPieceIds: z.array(z.number()),
  assignmentStockTypeIds: z.array(z.number()),
  optionalStockTypeIds: z.array(z.number()),
})

export type SetSummary = z.infer<typeof setSummarySchema>

export const setStockLineSchema = z.object({
  id: z.number(),
  materialTypeId: z.number(),
  materialTypeName: z.string(),
  stockVariant: z.record(z.string(), z.string()).default({}),
  role: z.enum(['assignment', 'optional']),
  quantity: z.number(),
})

export const setDetailSchema = setSummarySchema.extend({
  photos: z.array(photoMetaSchema).optional(),
  assignmentPieces: z.array(pieceSchema),
  optionalPieces: z.array(pieceSchema),
  assignmentStock: z.array(setStockLineSchema),
  optionalStock: z.array(setStockLineSchema),
})

export type SetDetail = z.infer<typeof setDetailSchema>
