import { z } from 'zod'

export const categorySchema = z.object({
  id: z.number(),
  name: z.string(),
})

export type Category = z.infer<typeof categorySchema>

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
  variantLabel: z.string().nullable(),
  variantValues: z.array(z.string()),
})

export type MaterialType = z.infer<typeof materialTypeSchema>

export const pieceSchema = z.object({
  id: z.number(),
  materialTypeId: z.number(),
  materialTypeName: z.string(),
  name: z.string(),
  variant: z.string().nullable(),
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

export const stockRowSchema = z.object({
  materialTypeId: z.number(),
  materialTypeName: z.string(),
  unit: z.string().nullable(),
  quantity: z.number(),
})

export type StockRow = z.infer<typeof stockRowSchema>
