import { AxiosError, AxiosHeaders } from 'axios'
import { describe, expect, it } from 'vitest'

import { shouldRetryQuery } from './client'

function failed(status?: number): AxiosError {
  const config = { headers: new AxiosHeaders() }
  const response = status === undefined ? undefined : { status, statusText: '', headers: {}, config, data: {} }
  return new AxiosError('failed', 'ERR', config, null, response)
}

describe('shouldRetryQuery', () => {
  it('shows 4xx at once', () => {
    for (const status of [401, 403, 404, 409]) expect(shouldRetryQuery(0, failed(status))).toBe(false)
  })

  it('retries server errors and lost connections twice', () => {
    expect(shouldRetryQuery(0, failed(502))).toBe(true)
    expect(shouldRetryQuery(1, failed())).toBe(true)
    expect(shouldRetryQuery(2, failed(500))).toBe(false)
  })
})
