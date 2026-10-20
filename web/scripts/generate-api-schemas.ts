// Writes src/api/generated/schemas.ts from the API's OpenAPI document (#16).
// Run after `lamathek openapi`: npm run generate:api
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { generateZodModule, type OpenApiDocument } from './api-schemas.ts'

const here = dirname(fileURLToPath(import.meta.url))
const source = resolve(here, '../../server/lamathek/domain/openapi.json')
const target = resolve(here, '../src/api/generated/schemas.ts')

const document = JSON.parse(readFileSync(source, 'utf8')) as OpenApiDocument
mkdirSync(dirname(target), { recursive: true })
writeFileSync(target, generateZodModule(document))
console.log(`Wrote ${target}`)
