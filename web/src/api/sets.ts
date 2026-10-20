import { api } from './client'
import { setDetailSchema, setSummarySchema, type SetDetail, type SetSummary } from '../schemas/set'

export async function fetchSets(inventoryId: number): Promise<SetSummary[]> {
  const response = await api.get(`/api/inventories/${inventoryId}/sets`)
  return setSummarySchema.array().parse(response.data)
}

export async function createSet(
  inventoryId: number,
  payload: { name: string; shortName?: string | null },
): Promise<SetDetail> {
  const response = await api.post(`/api/inventories/${inventoryId}/sets`, {
    name: payload.name,
    shortName: payload.shortName ?? null,
  })
  return setDetailSchema.parse(response.data)
}

export async function fetchSet(setId: number): Promise<SetDetail> {
  const response = await api.get(`/api/sets/${setId}`)
  return setDetailSchema.parse(response.data)
}

export async function updateSet(
  setId: number,
  payload: { name: string; shortName?: string | null },
): Promise<SetDetail> {
  const response = await api.patch(`/api/sets/${setId}`, {
    name: payload.name,
    shortName: payload.shortName ?? null,
  })
  return setDetailSchema.parse(response.data)
}

export async function deleteSet(setId: number): Promise<void> {
  await api.delete(`/api/sets/${setId}`)
}

export async function setPieceOnSet(
  setId: number,
  pieceId: number,
  role: 'assignment' | 'optional' | null,
): Promise<void> {
  await api.put(`/api/sets/${setId}/pieces`, { pieceId, role })
}

export async function upsertSetStockLine(
  setId: number,
  payload: {
    materialTypeId: number
    role: 'assignment' | 'optional'
    quantity: number
    variant?: Record<string, string>
  },
): Promise<SetDetail> {
  const response = await api.put(`/api/sets/${setId}/stock-lines`, payload)
  return setDetailSchema.parse(response.data)
}
