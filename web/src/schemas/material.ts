import { z } from 'zod'

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
  variants: z.array(variantAxisSchema),
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
})

export type Piece = z.infer<typeof pieceSchema>

export const repairSchema = z.object({
  id: z.number(),
  recordedOn: z.string(),
  note: z.string().nullable(),
})

export const damageSchema = z.object({
  id: z.number(),
  recordedOn: z.string(),
  note: z.string().nullable(),
  severe: z.boolean(),
  open: z.boolean(),
  repair: repairSchema.nullable(),
})

export const pieceDetailSchema = pieceSchema.extend({
  inventoryId: z.number(),
  damages: z.array(damageSchema),
})

export type Damage = z.infer<typeof damageSchema>
export type PieceDetail = z.infer<typeof pieceDetailSchema>

export const stockLotSchema = z.object({
  id: z.number(),
  label: z.string().nullable(),
  variant: variantMapSchema,
  quantity: z.number(),
})

export const stockRowSchema = z.object({
  materialTypeId: z.number(),
  materialTypeName: z.string(),
  unit: z.string().nullable(),
  variants: z.array(variantAxisSchema),
  quantity: z.number(),
  lots: z.array(stockLotSchema),
})

export type StockLot = z.infer<typeof stockLotSchema>

export type StockRow = z.infer<typeof stockRowSchema>
