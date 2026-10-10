import { api } from './client'
import {
  inventoryPermissionsSchema,
  inventorySchema,
  inventoryWriteSchema,
  type Inventory,
  type InventoryWritePayload,
} from '../schemas/inventory'

function writeBody(payload: InventoryWritePayload) {
  const parsed = inventoryWriteSchema.parse(payload)
  return {
    name: parsed.name,
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

export async function fetchInventory(id: number): Promise<Inventory> {
  const response = await api.get(`/api/inventories/${id}`)
  return inventorySchema.parse(response.data)
}

export async function updateInventory(
  id: number,
  payload: InventoryWritePayload,
): Promise<Inventory> {
  const response = await api.patch(`/api/inventories/${id}`, writeBody(payload))
  return inventorySchema.parse(response.data)
}

export async function fetchInventoryPermissions(id: number): Promise<number[]> {
  const response = await api.get(`/api/inventories/${id}/permissions`)
  return inventoryPermissionsSchema.parse(response.data).userIds
}

export async function replaceInventoryPermissions(
  id: number,
  userIds: number[],
): Promise<number[]> {
  const response = await api.put(`/api/inventories/${id}/permissions`, { userIds })
  return inventoryPermissionsSchema.parse(response.data).userIds
}

export async function deleteInventory(id: number): Promise<void> {
  await api.delete(`/api/inventories/${id}`)
}
