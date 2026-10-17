import { api } from './client'
import { managedUserSchema, userSchema, type ManagedUser, type User } from '../schemas/user'

export async function fetchUsers(): Promise<ManagedUser[]> {
  const response = await api.get('/api/users')
  return managedUserSchema.array().parse(response.data)
}

export async function createLocalUser(payload: {
  name: string
  phone: string
  email: string
}): Promise<User> {
  const response = await api.post('/api/users', payload)
  return userSchema.parse(response.data)
}

export async function searchUsers(query: string): Promise<User[]> {
  const response = await api.get('/api/users/search', { params: { q: query } })
  return userSchema.array().parse(response.data)
}

export async function updateUserContact(
  userId: number,
  payload: { phone: string; email: string },
): Promise<User> {
  const response = await api.patch(`/api/users/${userId}`, payload)
  return userSchema.parse(response.data)
}

export async function setUserSuperuser(
  userId: number,
  isSuperuser: boolean,
): Promise<User> {
  const response = await api.patch(`/api/users/${userId}`, { isSuperuser })
  return userSchema.parse(response.data)
}

export async function grantUserInventory(
  userId: number,
  inventoryId: number,
): Promise<ManagedUser> {
  const response = await api.post(`/api/users/${userId}/inventories`, { inventoryId })
  return managedUserSchema.parse(response.data)
}

export async function mergeLocalUser(sourceUserId: number, targetUserId: number): Promise<User> {
  const response = await api.post(`/api/users/${sourceUserId}/merge`, { targetUserId })
  return userSchema.parse(response.data)
}

export async function revokeUserInventory(
  userId: number,
  inventoryId: number,
): Promise<ManagedUser> {
  const response = await api.delete(`/api/users/${userId}/inventories/${inventoryId}`)
  return managedUserSchema.parse(response.data)
}
