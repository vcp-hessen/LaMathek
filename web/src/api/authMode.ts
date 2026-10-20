import { api } from './client'
import { authModeSchema, type AuthMode } from './generated/schemas'

export async function fetchAuthMode(): Promise<AuthMode> {
  const response = await api.get('/api/auth/mode')
  return authModeSchema.parse(response.data)
}
