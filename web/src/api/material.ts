import { api } from './client'
import {
  categorySchema,
  materialTypeSchema,
  pieceDetailSchema,
  pieceSchema,
  stockRowSchema,
  type Category,
  type MaterialType,
  type Piece,
  type PieceDetail,
  type StockRow,
} from '../schemas/material'

export type MaterialTypeWritePayload = {
  name: string
  tracking: 'piece' | 'stock'
  variantLabel?: string | null
  variantValues?: string[]
  shortName?: string | null
  description?: string | null
  unit?: string | null
  consumable?: boolean
  categoryId?: number | null
  categoryName?: string | null
}

export async function fetchCategories(): Promise<Category[]> {
  const response = await api.get('/api/categories')
  return categorySchema.array().parse(response.data)
}

export async function fetchMaterialTypes(inventoryId: number): Promise<MaterialType[]> {
  const response = await api.get(`/api/inventories/${inventoryId}/material-types`)
  return materialTypeSchema.array().parse(response.data)
}

export async function createMaterialType(
  inventoryId: number,
  payload: MaterialTypeWritePayload,
): Promise<MaterialType> {
  const response = await api.post(`/api/inventories/${inventoryId}/material-types`, payload)
  return materialTypeSchema.parse(response.data)
}

export async function updateMaterialType(
  id: number,
  payload: Partial<MaterialTypeWritePayload>,
): Promise<MaterialType> {
  const response = await api.patch(`/api/material-types/${id}`, payload)
  return materialTypeSchema.parse(response.data)
}

export async function deleteMaterialType(id: number): Promise<void> {
  await api.delete(`/api/material-types/${id}`)
}

export async function fetchPieces(inventoryId: number): Promise<Piece[]> {
  const response = await api.get(`/api/inventories/${inventoryId}/pieces`)
  return pieceSchema.array().parse(response.data)
}

export async function fetchPiece(pieceId: number): Promise<PieceDetail> {
  const response = await api.get(`/api/pieces/${pieceId}`)
  return pieceDetailSchema.parse(response.data)
}

export async function createPieceDamage(
  pieceId: number,
  payload: { recordedOn: string; severe: boolean; note?: string },
): Promise<void> {
  await api.post(`/api/pieces/${pieceId}/damages`, payload)
}

export async function createDamageRepair(
  damageId: number,
  payload: { recordedOn: string; note?: string },
): Promise<void> {
  await api.post(`/api/damages/${damageId}/repairs`, payload)
}

export async function createPiece(
  inventoryId: number,
  payload: { materialTypeId: number; name: string; variant?: string | null },
): Promise<Piece> {
  const response = await api.post(`/api/inventories/${inventoryId}/pieces`, payload)
  return pieceSchema.parse(response.data)
}

export type CreatePiecesBatchPayload = {
  materialTypeId: number
  count: number
  namePattern: string
  variant?: string | null
  setId?: number
  setName?: string
  setShortName?: string | null
}

export async function createPiecesBatch(
  inventoryId: number,
  payload: CreatePiecesBatchPayload,
): Promise<{ pieces: Piece[]; setId?: number }> {
  const response = await api.post(`/api/inventories/${inventoryId}/pieces/batch`, payload)
  const data = response.data as { pieces: unknown[]; setId?: number }
  return {
    pieces: pieceSchema.array().parse(data.pieces),
    setId: data.setId,
  }
}

export async function updatePiece(
  id: number,
  payload: {
    name?: string
    materialTypeId?: number
    variant?: string | null
  },
): Promise<Piece> {
  const response = await api.patch(`/api/pieces/${id}`, payload)
  return pieceSchema.parse(response.data)
}

export async function deletePiece(id: number): Promise<void> {
  await api.delete(`/api/pieces/${id}`)
}

export async function fetchStocks(inventoryId: number): Promise<StockRow[]> {
  const response = await api.get(`/api/inventories/${inventoryId}/stocks`)
  return stockRowSchema.array().parse(response.data)
}

export async function setStockQuantity(
  inventoryId: number,
  materialTypeId: number,
  quantity: number,
): Promise<StockRow> {
  const response = await api.put(
    `/api/inventories/${inventoryId}/stocks/${materialTypeId}`,
    { quantity },
  )
  return stockRowSchema.parse(response.data)
}
