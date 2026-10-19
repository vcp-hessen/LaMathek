import { z } from 'zod'

import { loanWarningSchema } from './loan'
import { photoMetaSchema } from './photo'

export const categorySchema = z.object({
  id: z.number(),
  name: z.string(),
})

export type Category = z.infer<typeof categorySchema>

export const variantAxisSchema = z.object({
  label: z.string(),
  values: z.array(z.string()),
})

export type VariantAxis = z.infer<typeof variantAxisSchema>

export const variantMapSchema = z.record(z.string(), z.string())

export const materialItemStatusSchema = z.enum(['active', 'retired'])
export type MaterialItemStatus = z.infer<typeof materialItemStatusSchema>

export const materialItemFieldsSchema = z.object({
  acquiredYear: z.number().nullable(),
  note: z.string().nullable(),
  source: z.string().nullable(),
  status: materialItemStatusSchema,
  serialNumber: z.string().nullable(),
  newValueCents: z.number().nullable(),
})

export type MaterialItemFields = z.infer<typeof materialItemFieldsSchema>

export const materialTypeSchema = z.object({
  id: z.number(),
  inventoryId: z.number(),
  name: z.string(),
  shortName: z.string().nullable(),
  description: z.string().nullable(),
  tracking: z.enum(['piece', 'stock']),
  unit: z.string().nullable(),
  consumable: z.boolean(),
  categoryId: z.number().nullable(),
  categoryName: z.string().nullable(),
  manufacturer: z.string().nullable(),
  modelName: z.string().nullable(),
  variants: z.array(variantAxisSchema),
  coverPhotoId: z.number().nullish(),
  usageCount: z.number().optional(),
  photos: z.array(photoMetaSchema).optional(),
})

export type MaterialType = z.infer<typeof materialTypeSchema>

export const pieceSchema = z.object({
  id: z.number(),
  materialTypeId: z.number(),
  materialTypeName: z.string(),
  name: z.string(),
  variant: variantMapSchema,
  setId: z.number().nullable(),
  setRole: z.enum(['assignment', 'optional']).nullable(),
  setName: z.string().nullable(),
  coverPhotoId: z.number().nullish(),
  lost: z.boolean().optional(),
  ...materialItemFieldsSchema.shape,
})

export type Piece = z.infer<typeof pieceSchema>

export const repairSchema = z.object({
  id: z.number(),
  recordedOn: z.string(),
  note: z.string().nullable(),
  resolutionKind: z.string().optional(),
})

export const damageSchema = z.object({
  id: z.number(),
  recordedOn: z.string(),
  note: z.string().nullable(),
  severe: z.boolean(),
  kind: z.string().optional(),
  open: z.boolean(),
  repair: repairSchema.nullable(),
  photos: z.array(photoMetaSchema).optional(),
})

export const pieceDetailSchema = pieceSchema.extend({
  inventoryId: z.number(),
  photos: z.array(photoMetaSchema).optional(),
  damages: z.array(damageSchema),
  foundAgainEligible: z.boolean().optional(),
  warnings: z.array(loanWarningSchema).optional(),
})

export type Damage = z.infer<typeof damageSchema>
export type PieceDetail = z.infer<typeof pieceDetailSchema>

export const stockLotSchema = z.object({
  id: z.number(),
  label: z.string().nullable(),
  variant: variantMapSchema,
  /** Soll-Anzahl of the lot (never lowered by an open loss). */
  quantity: z.number(),
  /** Part of it that is lost and not yet resolved. */
  lostQuantity: z.number().optional(),
  coverPhotoId: z.number().nullish(),
  photos: z.array(photoMetaSchema).optional(),
  ...materialItemFieldsSchema.shape,
})

export const stockRowSchema = z.object({
  materialTypeId: z.number(),
  materialTypeName: z.string(),
  unit: z.string().nullable(),
  variants: z.array(variantAxisSchema),
  /** What can be lent: active lots minus open losses. */
  quantity: z.number(),
  lostQuantity: z.number().optional(),
  coverPhotoId: z.number().nullish(),
  lots: z.array(stockLotSchema),
})

/** Verlust or Verbrauch of a quantity, booked against a Mengenposten (D0009). */
export const stockLossSchema = z.object({
  id: z.number(),
  stockLotId: z.number(),
  materialTypeId: z.number(),
  loanLineId: z.number().nullable(),
  loanId: z.number().nullable(),
  kind: z.enum(['lost', 'consumed']),
  quantity: z.number(),
  recordedOn: z.string(),
  reason: z.string(),
  open: z.boolean(),
  resolution: z.string().nullable(),
  resolvedOn: z.string().nullable(),
  resolutionNote: z.string(),
})

export type StockLoss = z.infer<typeof stockLossSchema>

export type StockLot = z.infer<typeof stockLotSchema>

export type StockRow = z.infer<typeof stockRowSchema>
