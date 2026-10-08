import { z } from 'zod'
import { api } from './client'

const authModeSchema = z.object({
  devBypass: z.boolean(),
})

export async function fetchAuthMode(): Promise<{ devBypass: boolean }> {
  const response = await api.get('/api/auth/mode')
  return authModeSchema.parse(response.data)
}
