import { z } from 'zod'
import { api } from './client'

const geocodeSchema = z.object({
  latitude: z.number(),
  longitude: z.number(),
})

export async function geocodeAddress(query: string): Promise<{ latitude: number; longitude: number }> {
  const response = await api.get('/api/geocode', { params: { q: query } })
  return geocodeSchema.parse(response.data)
}
