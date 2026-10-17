import { api } from './client'
import { meSchema, type Me } from '../schemas/me'

export async function fetchMe(): Promise<Me | null> {
  const response = await api.get('/api/me', {
    validateStatus: (status) => status === 200 || status === 401,
  })
  if (response.status === 401) {
    return null
  }
  return meSchema.parse(response.data)
}

export async function patchMePhone(phone: string): Promise<Me> {
  const response = await api.patch('/api/me', { phone })
  return meSchema.parse(response.data)
}

export async function logout(): Promise<void> {
  await api.post('/logout')
}
