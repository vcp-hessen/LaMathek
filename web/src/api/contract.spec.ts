import { describe, expect, it } from 'vitest'

import openapi from '@shared/openapi.json'
import { generateZodModule, type OpenApiDocument } from '../../scripts/api-schemas'
import { BUNDESLAND_CODES } from '../utils/germanPublicHolidays'
import { calendarBundeslandSchema } from './generated/schemas'
import generated from './generated/schemas.ts?raw'

// The API contract (#16): server/lamathek/domain/openapi.json is generated from the
// Pydantic models (pytest checks that), src/api/generated/schemas.ts from it.
describe('API contract', () => {
  it('has generated zod schemas matching the OpenAPI document', () => {
    expect(
      generateZodModule(openapi as unknown as OpenApiDocument),
      'src/api/generated/schemas.ts is stale: run `npm run generate:api`',
    ).toBe(generated)
  })

  it('knows the same Bundesländer for holidays as the API', () => {
    expect([...BUNDESLAND_CODES].sort()).toEqual([...calendarBundeslandSchema.options].sort())
  })
})
