import { api } from './client'
import {
  inventoryPermissionsSchema,
  inventorySchema,
  type Inventory,
} from '../schemas/inventory'

export async function fetchInventories(): Promise<Inventory[]> {
  const response = await api.get('/api/inventories')
  return inventorySchema.array().parse(response.data)
}

export async function createInventory(name: string): Promise<Inventory> {
  const response = await api.post('/api/inventories', { name })
  return inventorySchema.parse(response.data)
}

export async function fetchInventory(id: number): Promise<Inventory> {
  const response = await api.get(`/api/inventories/${id}`)
  return inventorySchema.parse(response.data)
}

export async function renameInventory(id: number, name: string): Promise<Inventory> {
  const response = await api.patch(`/api/inventories/${id}`, { name })
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
