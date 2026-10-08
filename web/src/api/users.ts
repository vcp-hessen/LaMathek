import { api } from './client'
import { userSchema, type User } from '../schemas/user'

export async function fetchUsers(): Promise<User[]> {
  const response = await api.get('/api/users')
  return userSchema.array().parse(response.data)
}

export async function setUserSuperuser(
  userId: number,
  isSuperuser: boolean,
): Promise<User> {
  const response = await api.patch(`/api/users/${userId}`, { isSuperuser })
  return userSchema.parse(response.data)
}

export async function setUserRole(
  userId: number,
  role: 'materialwart' | 'verantwortliche',
): Promise<User> {
  const response = await api.patch(`/api/users/${userId}`, { role })
  return userSchema.parse(response.data)
}
