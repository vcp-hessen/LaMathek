import { describe, expect, it } from 'vitest'

import { formatDate, formatDateTime, localIsoDate } from './dates'

describe('dates', () => {
  it('uses the local calendar day, not UTC', () => {
    expect(localIsoDate(new Date(2026, 0, 1, 0, 30))).toBe('2026-01-01')
  })

  it('formats API dates without shifting them', () => {
    expect(formatDate('2026-10-20')).toBe('20.10.2026')
    expect(formatDate(null)).toBe('—')
  })

  it('formats timestamps with offset', () => {
    expect(formatDateTime('2026-10-20T09:15:00+00:00')).toMatch(/^20\.10\.26, \d{2}:15$/)
    expect(formatDateTime(null)).toBe('')
  })
})
