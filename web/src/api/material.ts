import { z } from 'zod'

import { api } from './client'
import { journalEntrySchema } from '../schemas/journal'
import {
  categorySchema,
  materialTypeSchema,
  pieceDetailSchema,
  pieceSchema,
  stockRowSchema,
  type Category,
  type MaterialItemStatus,
  type MaterialType,
  type Piece,
  type PieceDetail,
  type StockLoss,
  type StockRow,
  stockLossSchema,
} from '../schemas/material'

export type MaterialItemWriteFields = {
  acquiredYear?: number | null
  note?: string | null
  source?: string | null
  status?: MaterialItemStatus
  serialNumber?: string | null
  newValueCents?: number | null
}

export type MaterialTypeWritePayload = {
  name: string
  tracking: 'piece' | 'stock'
  variants?: { label: string; values: string[] }[]
  shortName?: string | null
  description?: string | null
  unit?: string | null
  consumable?: boolean
  categoryId?: number | null
  categoryName?: string | null
  manufacturer?: string | null
  modelName?: string | null
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

/** Full inventory list. For large inventories, add server-side q/page/pageSize and switch callers. */
export async function fetchPieces(inventoryId: number): Promise<Piece[]> {
  const response = await api.get(`/api/inventories/${inventoryId}/pieces`)
  return pieceSchema.array().parse(response.data)
}

export async function fetchPieceJournal(pieceId: number) {
  const response = await api.get(`/api/pieces/${pieceId}/journal`)
  return journalEntrySchema.array().parse(response.data)
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

export async function postPieceFoundAgain(
  pieceId: number,
  payload: { reason: string; recordedOn?: string },
): Promise<PieceDetail> {
  const response = await api.post(`/api/pieces/${pieceId}/found-again`, payload)
  return pieceDetailSchema.parse(response.data)
}

export async function postPieceWriteOff(
  pieceId: number,
  payload: { reason: string },
): Promise<PieceDetail> {
  const response = await api.post(`/api/pieces/${pieceId}/write-off`, payload)
  return pieceDetailSchema.parse(response.data)
}

export async function fetchStockLosses(
  inventoryId: number,
  materialTypeId: number,
): Promise<StockLoss[]> {
  const response = await api.get(
    `/api/inventories/${inventoryId}/stocks/${materialTypeId}/losses`,
  )
  return z.array(stockLossSchema).parse(response.data)
}

export async function resolveStockLoss(
  inventoryId: number,
  lossId: number,
  action: 'found-again' | 'write-off',
  payload: { reason: string; quantity?: number },
): Promise<StockLoss> {
  const response = await api.post(
    `/api/inventories/${inventoryId}/stock-losses/${lossId}/${action}`,
    payload,
  )
  return stockLossSchema.parse(response.data)
}

export async function createDamageRepair(
  damageId: number,
  payload: { recordedOn: string; note?: string },
): Promise<void> {
  await api.post(`/api/damages/${damageId}/repairs`, payload)
}

export async function createPiece(
  inventoryId: number,
  payload: {
    materialTypeId: number
    name: string
    variant?: Record<string, string>
  } & MaterialItemWriteFields,
): Promise<Piece> {
  const response = await api.post(`/api/inventories/${inventoryId}/pieces`, payload)
  return pieceSchema.parse(response.data)
}

export type CreatePiecesBatchPayload = {
  materialTypeId: number
  count: number
  namePattern: string
  variant?: Record<string, string>
  setId?: number
  setName?: string
  setShortName?: string | null
} & MaterialItemWriteFields

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
    variant?: Record<string, string>
  } & MaterialItemWriteFields,
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

export async function createStockLot(
  inventoryId: number,
  materialTypeId: number,
  payload: {
    label?: string | null
    variant?: Record<string, string>
    quantity: number
  } & MaterialItemWriteFields,
): Promise<StockRow> {
  const response = await api.post(
    `/api/inventories/${inventoryId}/stocks/${materialTypeId}/lots`,
    payload,
  )
  return stockRowSchema.parse(response.data)
}

export async function updateStockLot(
  inventoryId: number,
  lotId: number,
  payload: {
    label?: string | null
    variant?: Record<string, string>
    quantity: number
  } & MaterialItemWriteFields,
): Promise<StockRow> {
  const response = await api.patch(
    `/api/inventories/${inventoryId}/stock-lots/${lotId}`,
    payload,
  )
  return stockRowSchema.parse(response.data)
}

export async function deleteStockLot(inventoryId: number, lotId: number): Promise<void> {
  await api.delete(`/api/inventories/${inventoryId}/stock-lots/${lotId}`)
}
