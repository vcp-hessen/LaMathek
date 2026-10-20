import { api } from './client'
import { geocodeResultSchema, type GeocodeResult } from './generated/schemas'

export async function geocodeAddress(query: string): Promise<GeocodeResult> {
  const response = await api.get('/api/geocode', { params: { q: query } })
  return geocodeResultSchema.parse(response.data)
}
