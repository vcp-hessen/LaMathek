import { api } from './client'
import type { User } from '../schemas/user'
import {
  inventoryDetailSchema,
  inventoryPermissionsSchema,
  inventorySchema,
  inventoryWriteSchema,
  type Inventory,
  type InventoryDetail,
  type InventoryWritePayload,
} from '../schemas/inventory'

function writeBody(payload: InventoryWritePayload) {
  const parsed = inventoryWriteSchema.parse(payload)
  return {
    name: parsed.name,
    visibility: parsed.visibility,
    address: parsed.address ?? null,
    latitude: parsed.latitude ?? null,
    longitude: parsed.longitude ?? null,
    notes: parsed.notes ?? null,
  }
}

export async function fetchInventories(): Promise<Inventory[]> {
  const response = await api.get('/api/inventories')
  return inventorySchema.array().parse(response.data)
}

export async function createInventory(payload: InventoryWritePayload): Promise<Inventory> {
  const response = await api.post('/api/inventories', writeBody(payload))
  return inventorySchema.parse(response.data)
}

export async function fetchInventory(id: number): Promise<InventoryDetail> {
  const response = await api.get(`/api/inventories/${id}`)
  return inventoryDetailSchema.parse(response.data)
}

export async function updateInventory(
  id: number,
  payload: InventoryWritePayload,
): Promise<InventoryDetail> {
  const response = await api.patch(`/api/inventories/${id}`, writeBody(payload))
  return inventoryDetailSchema.parse(response.data)
}

export async function fetchInventoryAccess(id: number) {
  const response = await api.get(`/api/inventories/${id}/permissions`)
  const parsed = inventoryPermissionsSchema.parse(response.data)
  return { users: parsed.users, readers: parsed.readers }
}

export async function fetchInventoryPermissions(id: number): Promise<User[]> {
  return (await fetchInventoryAccess(id)).users
}

export async function replaceInventoryPermissions(
  id: number,
  userIds: number[],
  readerUserIds?: number[],
): Promise<User[]> {
  const response = await api.put(`/api/inventories/${id}/permissions`, {
    userIds,
    readerUserIds: readerUserIds ?? [],
  })
  return inventoryPermissionsSchema.parse(response.data).users
}

export async function deleteInventory(id: number): Promise<void> {
  await api.delete(`/api/inventories/${id}`)
}
