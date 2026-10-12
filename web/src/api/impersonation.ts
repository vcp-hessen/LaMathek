import { api } from './client'

export async function startImpersonation(userId: number, reason: string): Promise<void> {
  await api.post('/api/impersonation', { userId, reason })
}

export async function stopImpersonation(): Promise<void> {
  await api.delete('/api/impersonation')
}
